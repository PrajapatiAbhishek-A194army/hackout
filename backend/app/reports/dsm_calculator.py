import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import numpy as np

logger = logging.getLogger("backend.reports.dsm")

class CERC_DSM_Calculator:
    """
    Central Electricity Regulatory Commission (CERC) Deviation Settlement Mechanism (DSM)
    Calculator for Solar & Wind Power Plants in India.
    Implements 96-time block (15-minute interval) schedule and graded error band penalties.
    """

    DEFAULT_REFERENCE_TARIFF_INR_PER_MWH = 3000.0  # Rs 3.00 / kWh standard renewable PPA rate

    @staticmethod
    def get_time_range_for_block(block_idx: int) -> str:
        """
        Converts 1-indexed block (1..96) to 'HH:MM - HH:MM'.
        """
        start_minutes = (block_idx - 1) * 15
        end_minutes = block_idx * 15
        start_h, start_m = divmod(start_minutes, 60)
        end_h, end_m = divmod(end_minutes, 60)
        if end_h == 24:
            end_str = "24:00"
        else:
            end_str = f"{end_h:02d}:{end_m:02d}"
        return f"{start_h:02d}:{start_m:02d} - {end_str}"

    @classmethod
    def calculate_dsm(
        cls,
        plant_id: int,
        plant_name: str,
        plant_type: str,
        capacity_mw: float,
        target_date: date,
        hourly_schedule_mw: List[float],
        hourly_actual_mw: List[float],
        reference_tariff_inr_per_mwh: float = DEFAULT_REFERENCE_TARIFF_INR_PER_MWH
    ) -> Dict[str, Any]:
        """
        Interpolates 24-hour profiles into 96 15-minute time blocks and evaluates CERC DSM compliance.
        """
        if len(hourly_schedule_mw) < 24 or len(hourly_actual_mw) < 24:
            raise ValueError("Hourly schedule and actual profiles must contain at least 24 hours.")

        # Interpolate 24 hourly points into 96 15-minute time blocks
        x_hours = np.arange(24)
        x_15min = np.linspace(0, 23.75, 96)

        schedule_96 = np.interp(x_15min, x_hours, hourly_schedule_mw[:24])
        actual_96 = np.interp(x_15min, x_hours, hourly_actual_mw[:24])

        # Available capacity (AvC) typically equals plant rated capacity unless derated
        avc_mw = float(capacity_mw)

        time_blocks = []
        total_scheduled_mwh = 0.0
        total_actual_mwh = 0.0
        net_deviation_mwh = 0.0
        total_deviation_charges_inr = 0.0

        blocks_within_10 = 0
        blocks_10_to_15 = 0
        blocks_beyond_15 = 0
        abs_percentage_errors = []

        for b in range(1, 97):
            idx = b - 1
            sched_mw = round(max(0.0, float(schedule_96[idx])), 2)
            act_mw = round(max(0.0, float(actual_96[idx])), 2)
            time_range = cls.get_time_range_for_block(b)

            # Energy in MWh for 15 minutes (0.25 hour)
            sched_mwh = sched_mw * 0.25
            act_mwh = act_mw * 0.25
            total_scheduled_mwh += sched_mwh
            total_actual_mwh += act_mwh

            dev_mw = round(act_mw - sched_mw, 2)
            dev_mwh = dev_mw * 0.25
            net_deviation_mwh += dev_mwh

            # Error percentage relative to Available Capacity (AvC) per CERC regulations
            if avc_mw > 0:
                dev_pct = round((abs(dev_mw) / avc_mw) * 100.0, 2)
            else:
                dev_pct = 0.0
            abs_percentage_errors.append(dev_pct)

            # Graded regulatory DSM penalty bands
            # Band 1: <= 10% error -> Nil charge
            # Band 2: 10% - 15% error -> 10% of reference tariff on excess deviation
            # Band 3: > 15% error -> 20% of reference tariff on 10-15% portion + 50% on >15% portion
            if dev_pct <= 10.0:
                band = "within_10_pct"
                penalty_rate = 0.0
                charge = 0.0
                blocks_within_10 += 1
            elif dev_pct <= 15.0:
                band = "between_10_and_15_pct"
                excess_error_pct = dev_pct - 10.0
                excess_dev_mw = (excess_error_pct / 100.0) * avc_mw
                excess_dev_mwh = excess_dev_mw * 0.25
                penalty_rate = reference_tariff_inr_per_mwh * 0.10 # Rs 300 / MWh
                charge = round(excess_dev_mwh * penalty_rate, 2)
                blocks_10_to_15 += 1
            else:
                band = "beyond_15_pct"
                # Portion between 10% and 15%
                tier1_dev_mwh = (0.05 * avc_mw) * 0.25
                # Portion beyond 15%
                tier2_dev_mwh = ((dev_pct - 15.0) / 100.0 * avc_mw) * 0.25
                tier1_rate = reference_tariff_inr_per_mwh * 0.20 # Rs 600 / MWh
                tier2_rate = reference_tariff_inr_per_mwh * 0.50 # Rs 1500 / MWh
                charge = round((tier1_dev_mwh * tier1_rate) + (tier2_dev_mwh * tier2_rate), 2)
                penalty_rate = round(charge / (abs(dev_mwh) + 1e-6), 2)
                blocks_beyond_15 += 1

            total_deviation_charges_inr += charge

            time_blocks.append({
                "time_block": b,
                "time_range": time_range,
                "available_capacity_mw": avc_mw,
                "scheduled_generation_mw": sched_mw,
                "actual_generation_mw": act_mw,
                "deviation_mw": dev_mw,
                "deviation_pct": dev_pct,
                "deviation_band": band,
                "penalty_rate_inr_per_mwh": penalty_rate,
                "deviation_charge_inr": charge
            })

        mape = round(float(np.mean(abs_percentage_errors)), 2)

        # Rating determination
        compliance_pct = (blocks_within_10 / 96.0) * 100.0
        if compliance_pct >= 90.0:
            rating = "EXCELLENT"
        elif compliance_pct >= 75.0:
            rating = "COMPLIANT"
        else:
            rating = "HIGH_PENALTY_RISK"

        summary = {
            "plant_id": plant_id,
            "plant_name": plant_name,
            "plant_type": plant_type,
            "capacity_mw": avc_mw,
            "date": target_date.strftime("%Y-%m-%d"),
            "total_scheduled_mwh": round(total_scheduled_mwh, 2),
            "total_actual_mwh": round(total_actual_mwh, 2),
            "net_deviation_mwh": round(net_deviation_mwh, 2),
            "mean_absolute_percentage_error": mape,
            "blocks_within_permissible_band": blocks_within_10,
            "blocks_moderate_deviation": blocks_10_to_15,
            "blocks_critical_violation": blocks_beyond_15,
            "total_deviation_charges_inr": round(total_deviation_charges_inr, 2),
            "compliance_rating": rating
        }

        return {
            "summary": summary,
            "time_blocks": time_blocks
        }

dsm_calculator = CERC_DSM_Calculator()
