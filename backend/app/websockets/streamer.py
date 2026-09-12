import math
import random
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import numpy as np

from app.models.plant import Plant
from app.models.alert_recommendation import Alert
from app.schemas.telemetry import LiveGridTelemetry, LivePlantTelemetry, PlantWeatherTelemetry
from app.websockets.manager import connection_manager

logger = logging.getLogger("backend.websockets.streamer")

class TelemetryStreamer:
    """
    Physics-Grounded High-Resolution Telemetry Simulator & Broadcaster.
    Generates real-time operational state metrics conforming to Indian Grid Code:
      1. Grid Frequency: 50.00 Hz nominal target, standard deviation 0.02 Hz
      2. Solar diurnal curve with cloud flicker
      3. Wind turbulence and diurnal speed variation
      4. BESS co-dispatch dynamics
    """

    def __init__(self):
        # Base frequency state with mean reversion
        self._current_frequency = 50.012
        self._last_solar_mw = 0.0
        self._last_wind_mw = 0.0

    def generate_grid_telemetry(self, db: Optional[Session] = None) -> LiveGridTelemetry:
        """
        Generates All-India live grid operating parameters for the current instant.
        """
        now = datetime.now(timezone(timedelta(hours=5, minutes=30))) # IST
        hour = now.hour + now.minute / 60.0

        # 1. Grid Frequency (Mean-Reverting Ornstein-Uhlenbeck Process around 50.00 Hz)
        target_f = 50.000
        reversion_speed = 0.35
        volatility = 0.015
        dW = random.gauss(0, 1)
        self._current_frequency += reversion_speed * (target_f - self._current_frequency) + volatility * dW
        # Keep strictly within IEGC operating band (49.85 - 50.15 Hz)
        self._current_frequency = round(max(49.88, min(50.12, self._current_frequency)), 3)

        if self._current_frequency >= 50.05:
            freq_status = "HIGH"
        elif self._current_frequency <= 49.90:
            freq_status = "LOW"
        else:
            freq_status = "NORMAL"

        # 2. National Demand Curve (MW) - Peak ~225 GW, Min ~160 GW
        demand_diurnal = math.sin((hour - 8.0) / 12.0 * math.pi)
        base_demand = 195000.0 + (30000.0 * demand_diurnal) + random.gauss(0, 500)
        demand_mw = round(base_demand, 1)

        # 3. National Solar Generation Curve (MW) - Peak ~68 GW at noon
        if 6.0 <= hour <= 18.25:
            solar_rad = math.sin((hour - 6.0) / 12.25 * math.pi)
            cloud_noise = 1.0 - (random.uniform(0.0, 0.12) if random.random() < 0.25 else 0.0)
            solar_mw = round(68000.0 * (solar_rad ** 1.15) * cloud_noise, 1)
        else:
            solar_mw = 0.0

        # 4. National Wind Generation Curve (MW) - Variable 22 - 35 GW
        wind_diurnal = math.sin((hour - 14.0) / 24.0 * 2 * math.pi) * 4000.0
        wind_mw = round(max(15000.0, 27000.0 + wind_diurnal + random.gauss(0, 350)), 1)

        total_re_mw = round(solar_mw + wind_mw, 1)
        re_penetration_pct = round((total_re_mw / demand_mw) * 100.0, 2)

        # 5. BESS Co-Dispatch (Negative = Charging, Positive = Discharging)
        if 11.0 <= hour <= 14.5:
            # Solar trough charging
            bess_mw = round(-3500.0 + random.gauss(0, 150), 1)
        elif 18.5 <= hour <= 22.0:
            # Evening peak discharging
            bess_mw = round(4200.0 + random.gauss(0, 150), 1)
        else:
            bess_mw = round(random.gauss(0, 50), 1)

        # Ramp rate calculation
        if self._last_solar_mw > 0:
            ramp_delta = round((total_re_mw - (self._last_solar_mw + self._last_wind_mw)), 1)
        else:
            ramp_delta = round(random.uniform(-15.0, 25.0), 1)
        self._last_solar_mw = solar_mw
        self._last_wind_mw = wind_mw

        # Active alerts count
        active_alerts = 0
        if db:
            try:
                active_alerts = db.query(Alert).filter(Alert.status == "active").count()
            except Exception:
                active_alerts = 2

        return LiveGridTelemetry(
            timestamp=datetime.now(),
            grid_frequency_hz=self._current_frequency,
            frequency_status=freq_status,
            national_demand_mw=demand_mw,
            total_renewable_mw=total_re_mw,
            total_solar_mw=solar_mw,
            total_wind_mw=wind_mw,
            renewable_penetration_pct=re_penetration_pct,
            bess_net_dispatch_mw=bess_mw,
            ramp_rate_mw_per_min=ramp_delta,
            active_alerts_count=active_alerts
        )

    def generate_plant_telemetry(self, plant: Plant) -> LivePlantTelemetry:
        """
        Generates realistic instant telemetry for a specific renewable facility.
        """
        now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
        hour = now.hour + now.minute / 60.0
        cap_mw = float(plant.capacity_mw)
        ptype = plant.plant_type.lower()

        # Environmental sensors
        if 6.0 <= hour <= 18.25:
            elev = math.sin((hour - 6.0) / 12.25 * math.pi)
            ghi = round(max(0.0, 950.0 * elev + random.gauss(0, 15)), 1)
            temp = round(26.0 + elev * 12.0 + random.gauss(0, 0.5), 1)
            cloud = round(max(0.0, min(100.0, 15.0 + random.gauss(0, 5))), 1)
        else:
            ghi = 0.0
            temp = round(22.0 + random.gauss(0, 0.5), 1)
            cloud = 10.0

        wind_spd = round(max(1.5, 7.5 + math.sin(hour / 3.0) * 3.0 + random.gauss(0, 0.6)), 2)

        # Plant generation model
        if ptype == "solar":
            gen_fraction = (ghi / 1000.0) * 0.92
            gen_mw = round(min(cap_mw, max(0.0, cap_mw * gen_fraction + random.gauss(0, cap_mw * 0.005))), 2)
            bess_soc = round(min(90.0, max(20.0, 25.0 + (hour - 6.0) * 5.0 if hour >= 6.0 else 25.0)), 1)
            bess_pwr = round(-0.15 * cap_mw if 11.0 <= hour <= 14.5 else (0.15 * cap_mw if 18.5 <= hour <= 21.5 else 0.0), 1)
        elif ptype == "wind":
            # Cubic power curve
            if wind_spd < 3.0 or wind_spd > 25.0:
                gen_fraction = 0.0
            elif wind_spd >= 12.0:
                gen_fraction = 1.0
            else:
                gen_fraction = ((wind_spd - 3.0) / 9.0) ** 2.2
            gen_mw = round(min(cap_mw, max(0.0, cap_mw * gen_fraction + random.gauss(0, cap_mw * 0.008))), 2)
            bess_soc = 55.0
            bess_pwr = 0.0
        else: # Hybrid
            solar_frac = (ghi / 1000.0) * 0.92
            wind_frac = ((max(3.0, min(12.0, wind_spd)) - 3.0) / 9.0) ** 2.0
            gen_mw = round(min(cap_mw, (cap_mw * 0.6 * solar_frac) + (cap_mw * 0.4 * wind_frac)), 2)
            bess_soc = 60.0
            bess_pwr = round(random.gauss(0, 5), 1)

        cuf = round((gen_mw / cap_mw * 100.0) if cap_mw > 0 else 0.0, 2)

        status = "NORMAL"
        if cuf >= 95.0:
            status = "CURTAILED" # Approaching maximum transmission evacuation capacity

        return LivePlantTelemetry(
            plant_id=plant.id,
            plant_code=plant.code,
            plant_name=plant.name,
            plant_type=plant.plant_type,
            capacity_mw=cap_mw,
            timestamp=datetime.now(),
            current_generation_mw=gen_mw,
            capacity_factor_pct=cuf,
            weather=PlantWeatherTelemetry(
                irradiance_ghi=ghi,
                wind_speed_ms=wind_spd,
                ambient_temp_c=temp,
                cloud_cover_pct=cloud
            ),
            bess_soc_pct=bess_soc,
            bess_power_mw=bess_pwr,
            operational_status=status
        )

    async def broadcast_tick(self, db: Session) -> Dict[str, Any]:
        """
        Generates and broadcasts a full synchronized real-time frame
        across all topics (global_grid, plant:{id}, alerts).
        """
        # 1. Global Grid Broadcast
        grid_data = self.generate_grid_telemetry(db)
        await connection_manager.broadcast_to_topic(
            topic="global_grid",
            message={
                "type": "grid_telemetry",
                "data": grid_data.model_dump(mode="json")
            }
        )

        # 2. Plant-Level Broadcasts
        plants = db.query(Plant).filter(Plant.status == "active").all()
        plant_telemetries = []
        for p in plants:
            plant_data = self.generate_plant_telemetry(p)
            plant_telemetries.append(plant_data)

            # Broadcast to specific plant channel
            await connection_manager.broadcast_to_topic(
                topic=f"plant:{p.id}",
                message={
                    "type": "plant_telemetry",
                    "data": plant_data.model_dump(mode="json")
                }
            )

        return {
            "grid": grid_data.model_dump(mode="json"),
            "plants_count": len(plant_telemetries),
            "timestamp": datetime.now().isoformat()
        }

telemetry_streamer = TelemetryStreamer()
