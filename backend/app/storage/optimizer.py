import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.plant import Plant
from app.services.forecast_engine import forecast_engine
from app.storage.battery_model import BatteryStorageConfig, StateOfChargeTracker

logger = logging.getLogger("backend.storage.optimizer")

class BESSDispatchOptimizer:
    """
    Battery Energy Storage System (BESS) Co-Optimization & Dispatch Engine.
    Jointly optimizes:
      1. Curtailment mitigation (absorbing generation exceeding transmission evacuation limits)
      2. Time-of-Day (ToD) merchant price arbitrage (charging during solar mid-day trough, discharging during evening peak)
      3. Dynamic State-of-Charge (SoC) management and battery cell degradation control
    """

    @staticmethod
    def get_default_indian_tariff(hour_of_day: int) -> float:
        """
        Standardized Indian Energy Exchange (IEX) Day-Ahead / Time-of-Day tariff curve (INR/MWh).
          - Night off-peak (23:00 - 06:00): Rs 2,500 / MWh (Rs 2.50/kWh)
          - Morning peak (06:00 - 10:00): Rs 5,500 / MWh (Rs 5.50/kWh)
          - Solar trough (10:00 - 15:00): Rs 2,200 / MWh (Rs 2.20/kWh) - solar surplus
          - Normal day (15:00 - 18:00): Rs 4,800 / MWh (Rs 4.80/kWh)
          - Evening peak (18:00 - 23:00): Rs 8,500 / MWh (Rs 8.50/kWh) - evening demand surge
        """
        if 23 <= hour_of_day or hour_of_day < 6:
            return 2500.0
        elif 6 <= hour_of_day < 10:
            return 5500.0
        elif 10 <= hour_of_day < 15:
            return 2200.0
        elif 15 <= hour_of_day < 18:
            return 4800.0
        else: # 18 to 23
            return 8500.0

    @classmethod
    def optimize_dispatch(
        cls,
        generation_profile: List[float],
        grid_capacity_limit_mw: float,
        bess_config: BatteryStorageConfig,
        timestamps: Optional[List[datetime]] = None,
        tariffs_inr_per_mwh: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Execute forward look-ahead co-optimization of battery charging and discharging.
        """
        T = len(generation_profile)
        if T == 0:
            raise ValueError("Generation profile cannot be empty.")

        now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
        if timestamps is None or len(timestamps) < T:
            timestamps = [now + timedelta(hours=i) for i in range(T)]

        if tariffs_inr_per_mwh is None or len(tariffs_inr_per_mwh) < T:
            tariffs = []
            for ts in timestamps:
                if ts.tzinfo is not None:
                    ist_hour = ts.astimezone(timezone(timedelta(hours=5, minutes=30))).hour
                else:
                    ist_hour = (ts.hour + 5 + (1 if ts.minute + 30 >= 60 else 0)) % 24
                tariffs.append(cls.get_default_indian_tariff(ist_hour))
        else:
            tariffs = tariffs_inr_per_mwh[:T]

        # Initialize battery physical tracker
        tracker = StateOfChargeTracker(bess_config)
        P_bess = bess_config.power_capacity_mw
        P_grid_max = grid_capacity_limit_mw

        # Identify arbitrage opportunities: high price quantile vs low price quantile
        tariff_arr = np.array(tariffs)
        low_price_threshold = float(np.percentile(tariff_arr, 35))
        high_price_threshold = float(np.percentile(tariff_arr, 65))

        hourly_results = []
        gross_charging_cost = 0.0
        gross_discharge_revenue = 0.0
        unmitigated_curtailment_total = 0.0
        mitigated_curtailment_total = 0.0

        for t in range(T):
            gen_mw = max(0.0, float(generation_profile[t]))
            ts = timestamps[t]
            current_tariff = tariffs[t]

            # Baseline unmitigated curtailment without BESS
            unmitigated_curt = max(0.0, gen_mw - P_grid_max)
            unmitigated_curtailment_total += unmitigated_curt

            charge_cmd = 0.0
            discharge_cmd = 0.0

            # -------------------------------------------------------------
            # PRIORITY 1: Absorb Over-Generation Curtailment (Free Energy)
            # -------------------------------------------------------------
            if unmitigated_curt > 0:
                headroom_mw = tracker.available_charge_headroom_mwh()  # MWh per 1 hour = MW
                charge_cmd = min(P_bess, unmitigated_curt, headroom_mw)
                # Cost of charging curtailed energy is 0 (it would be lost)
                charged_market_mw = 0.0
            else:
                # -------------------------------------------------------------
                # PRIORITY 2: Merchant Arbitrage Charging
                # -------------------------------------------------------------
                headroom_mw = tracker.available_charge_headroom_mwh()
                # Look-ahead: reserve capacity if significant curtailment is expected soon (next 10h)
                upcoming_curtailment = sum(
                    max(0.0, float(generation_profile[future_t]) - P_grid_max)
                    for future_t in range(t + 1, min(T, t + 10))
                )
                reserved_headroom = min(headroom_mw, upcoming_curtailment)
                effective_headroom = max(0.0, headroom_mw - reserved_headroom)

                if current_tariff <= low_price_threshold and effective_headroom > 5.0:
                    # Charge from on-site generation or cheap grid
                    avail_gen = min(P_bess, gen_mw, effective_headroom)
                    charge_cmd = min(P_bess, effective_headroom, max(avail_gen, P_bess * 0.7))
                    charged_market_mw = charge_cmd
                else:
                    charged_market_mw = 0.0

            # -------------------------------------------------------------
            # PRIORITY 3: Merchant Arbitrage Discharging
            # -------------------------------------------------------------
            if charge_cmd == 0.0 and current_tariff >= high_price_threshold:
                avail_discharge = tracker.available_discharge_capacity_mwh()
                grid_headroom = max(0.0, P_grid_max - gen_mw)
                discharge_cmd = min(P_bess, avail_discharge, grid_headroom)

            # Step physical battery model
            step_stats = tracker.step(charge_mw=charge_cmd, discharge_mw=discharge_cmd, dt_hours=1.0)
            eff_charge = step_stats["effective_charge_mw"]
            eff_discharge = step_stats["effective_discharge_mw"]

            # Actual power injected into transmission grid
            net_grid_mw = round(gen_mw - eff_charge + eff_discharge, 2)

            # Remaining curtailment after BESS mitigation
            mitigated_curt = max(0.0, net_grid_mw - P_grid_max)
            mitigated_curtailment_total += mitigated_curt
            net_grid_mw = min(P_grid_max, net_grid_mw)

            # Financial cash flow
            # Only pay for non-curtailed market charging
            market_charge_portion = min(eff_charge, max(0.0, eff_charge - unmitigated_curt))
            step_charge_cost = market_charge_portion * current_tariff
            step_discharge_rev = eff_discharge * current_tariff
            step_cash_flow = round(step_discharge_rev - step_charge_cost, 2)

            gross_charging_cost += step_charge_cost
            gross_discharge_revenue += step_discharge_rev

            hourly_results.append({
                "hour_index": t,
                "timestamp": ts,
                "generation_mw": round(gen_mw, 2),
                "grid_limit_mw": round(P_grid_max, 2),
                "bess_charge_mw": round(eff_charge, 2),
                "bess_discharge_mw": round(eff_discharge, 2),
                "net_grid_mw": net_grid_mw,
                "curtailment_unmitigated_mw": round(unmitigated_curt, 2),
                "curtailment_mitigated_mw": round(mitigated_curt, 2),
                "stored_energy_mwh": step_stats["stored_energy_mwh"],
                "soc_pct": step_stats["soc_pct"],
                "tariff_inr_per_mwh": round(current_tariff, 2),
                "cash_flow_inr": step_cash_flow
            })

        # Summary Financial & Operating Calculations
        gross_profit = gross_discharge_revenue - gross_charging_cost
        degradation_cost = tracker.total_discharged_mwh * 1000.0 * bess_config.degradation_cost_inr_per_kwh
        net_profit = gross_profit - degradation_cost

        avoided_curtailment_mwh = max(0.0, unmitigated_curtailment_total - mitigated_curtailment_total)
        curt_reduction_pct = (avoided_curtailment_mwh / unmitigated_curtailment_total * 100.0) if unmitigated_curtailment_total > 0 else 100.0

        # Avoided curtailment financial value: priced at average peak tariff
        avg_peak_tariff = float(np.mean([t for t in tariffs if t >= high_price_threshold])) if high_price_threshold else 8000.0
        avoided_curtailment_value = avoided_curtailment_mwh * avg_peak_tariff
        total_economic_benefit = net_profit + avoided_curtailment_value

        financial_summary = {
            "gross_charging_cost_inr": round(gross_charging_cost, 2),
            "gross_discharge_revenue_inr": round(gross_discharge_revenue, 2),
            "arbitrage_gross_profit_inr": round(gross_profit, 2),
            "battery_degradation_cost_inr": round(degradation_cost, 2),
            "net_arbitrage_profit_inr": round(net_profit, 2),
            "total_charged_mwh": round(tracker.total_charged_mwh, 2),
            "total_discharged_mwh": round(tracker.total_discharged_mwh, 2),
            "avoided_curtailment_mwh": round(avoided_curtailment_mwh, 2),
            "curtailment_reduction_pct": round(curt_reduction_pct, 2),
            "avoided_curtailment_value_inr": round(avoided_curtailment_value, 2),
            "total_combined_economic_benefit_inr": round(total_economic_benefit, 2),
            "equivalent_full_cycles": round(tracker.equivalent_full_cycles, 2)
        }

        return {
            "horizon_hours": T,
            "financial_summary": financial_summary,
            "dispatch_schedule": hourly_results
        }

    @classmethod
    def optimize_plant_storage(
        cls,
        db: Session,
        plant_id: int,
        horizon_hours: int = 24,
        bess_power_mw: Optional[float] = None,
        bess_energy_mwh: Optional[float] = None,
        grid_limit_factor: float = 0.80
    ) -> Dict[str, Any]:
        """
        Run BESS co-optimization for a registered renewable plant in the database.
        """
        plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            raise ValueError(f"Plant with ID {plant_id} does not exist.")

        capacity_mw = float(plant.capacity_mw)

        # Auto-size BESS if not specified: 20% power rating, 4-hour duration
        p_mw = bess_power_mw if bess_power_mw is not None else round(capacity_mw * 0.20, 1)
        e_mwh = bess_energy_mwh if bess_energy_mwh is not None else round(p_mw * 4.0, 1)
        p_grid_max = round(capacity_mw * grid_limit_factor, 1)

        bess_config = BatteryStorageConfig(
            power_capacity_mw=p_mw,
            energy_capacity_mwh=e_mwh,
            round_trip_efficiency=0.90,
            min_soc_pct=10.0,
            max_soc_pct=90.0,
            initial_soc_pct=20.0,
            degradation_cost_inr_per_kwh=0.80
        )

        # Generate plant forecast
        fc = forecast_engine.generate_plant_forecast(
            db=db,
            plant_id=plant.id,
            horizon_hours=horizon_hours,
            save_to_db=True
        )

        generation_profile = [p["predicted_mw"] for p in fc["forecast_points"]]
        timestamps = [p["timestamp"] for p in fc["forecast_points"]]

        opt_res = cls.optimize_dispatch(
            generation_profile=generation_profile,
            grid_capacity_limit_mw=p_grid_max,
            bess_config=bess_config,
            timestamps=timestamps
        )

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "plant_capacity_mw": capacity_mw,
            "horizon_hours": horizon_hours,
            "bess_config": {
                "power_capacity_mw": bess_config.power_capacity_mw,
                "energy_capacity_mwh": bess_config.energy_capacity_mwh,
                "round_trip_efficiency": bess_config.round_trip_efficiency,
                "min_soc_pct": bess_config.min_soc_pct,
                "max_soc_pct": bess_config.max_soc_pct,
                "initial_soc_pct": bess_config.initial_soc_pct,
                "degradation_cost_inr_per_kwh": bess_config.degradation_cost_inr_per_kwh
            },
            "financial_summary": opt_res["financial_summary"],
            "dispatch_schedule": opt_res["dispatch_schedule"]
        }

# Singleton instance
bess_dispatch_optimizer = BESSDispatchOptimizer()
