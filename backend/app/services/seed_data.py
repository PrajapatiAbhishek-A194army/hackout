import math
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database.session import SessionLocal, engine
from app.database.base import Base
from app.models.region_state import Region, State
from app.models.plant import Plant
from app.models.weather import Weather
from app.models.forecast import Forecast
from app.models.alert_recommendation import Alert, Recommendation
from app.models.model_run import ModelRun
from app.models.user import User

def seed_database():
    """Seed initial Indian renewable assets, regions, forecasts, and alerts."""
    db: Session = SessionLocal()
    try:
        print("[SEED] Seeding database with Indian Renewable Infrastructure...")

        # 1. Regions
        regions_data = [
            {"code": "NR", "name": "Northern Region", "desc": "Covers Rajasthan, Punjab, Haryana, UP, Delhi, Himachal, J&K", "solar": 18500.0, "wind": 5200.0},
            {"code": "WR", "name": "Western Region", "desc": "Covers Gujarat, Maharashtra, Madhya Pradesh, Goa, Chhattisgarh", "solar": 24000.0, "wind": 14500.0},
            {"code": "SR", "name": "Southern Region", "desc": "Covers Tamil Nadu, Karnataka, Andhra Pradesh, Telangana, Kerala", "solar": 21000.0, "wind": 16800.0},
            {"code": "ER", "name": "Eastern Region", "desc": "Covers West Bengal, Odisha, Bihar, Jharkhand", "solar": 4200.0, "wind": 800.0},
            {"code": "NER", "name": "North-Eastern Region", "desc": "Covers Assam, Arunachal, Meghalaya, Manipur, Mizoram, Nagaland, Tripura", "solar": 950.0, "wind": 120.0},
        ]

        region_map = {}
        for r in regions_data:
            existing = db.query(Region).filter(Region.code == r["code"]).first()
            if not existing:
                existing = Region(
                    code=r["code"],
                    name=r["name"],
                    description=r["desc"],
                    installed_solar_mw=r["solar"],
                    installed_wind_mw=r["wind"]
                )
                db.add(existing)
                db.flush()
            region_map[r["code"]] = existing

        # 2. States
        states_data = [
            {"code": "RJ", "name": "Rajasthan", "region_code": "NR", "solar": 17800.0, "wind": 5100.0},
            {"code": "GJ", "name": "Gujarat", "region_code": "WR", "solar": 10500.0, "wind": 10400.0},
            {"code": "KA", "name": "Karnataka", "region_code": "SR", "solar": 8500.0, "wind": 5800.0},
            {"code": "TN", "name": "Tamil Nadu", "region_code": "SR", "solar": 6800.0, "wind": 10200.0},
            {"code": "MH", "name": "Maharashtra", "region_code": "WR", "solar": 5200.0, "wind": 5000.0},
            {"code": "AP", "name": "Andhra Pradesh", "region_code": "SR", "solar": 4600.0, "wind": 4100.0},
            {"code": "MP", "name": "Madhya Pradesh", "region_code": "WR", "solar": 3800.0, "wind": 2800.0},
        ]

        state_map = {}
        for s in states_data:
            existing = db.query(State).filter(State.code == s["code"]).first()
            if not existing:
                existing = State(
                    code=s["code"],
                    name=s["name"],
                    region_id=region_map[s["region_code"]].id,
                    installed_solar_mw=s["solar"],
                    installed_wind_mw=s["wind"]
                )
                db.add(existing)
                db.flush()
            state_map[s["code"]] = existing

        # 3. Renewable Generation Plants
        plants_data = [
            {
                "name": "Bhadla Solar Park",
                "code": "BHADLA_SOLAR_01",
                "plant_type": "solar",
                "capacity_mw": 2245.0,
                "latitude": 27.5397,
                "longitude": 71.9162,
                "elevation_m": 210.0,
                "technology": "Bifacial Mono-PERC with Single-Axis Tracker",
                "commissioning_year": 2020,
                "operator_name": "Saurya Urja / Adani / Azure",
                "region_code": "NR",
                "state_code": "RJ"
            },
            {
                "name": "Pavagada Solar Park (Shakti Sthala)",
                "code": "PAVAGADA_SOLAR_01",
                "plant_type": "solar",
                "capacity_mw": 2050.0,
                "latitude": 14.2811,
                "longitude": 77.2736,
                "elevation_m": 645.0,
                "technology": "Polycrystalline & High-Efficiency Mono-PERC",
                "commissioning_year": 2019,
                "operator_name": "KREDL / NTPC / SoftBank Energy",
                "region_code": "SR",
                "state_code": "KA"
            },
            {
                "name": "Muppandal Wind Farm",
                "code": "MUPPANDAL_WIND_01",
                "plant_type": "wind",
                "capacity_mw": 1500.0,
                "latitude": 8.2618,
                "longitude": 77.5484,
                "elevation_m": 45.0,
                "technology": "2.1MW - 3.3MW DFIG Low-Wind Turbines (Hub Height 120m)",
                "commissioning_year": 2014,
                "operator_name": "TANGEDCO / Suzlon / ReNew",
                "region_code": "SR",
                "state_code": "TN"
            },
            {
                "name": "Jaisalmer Wind Park",
                "code": "JAISALMER_WIND_01",
                "plant_type": "wind",
                "capacity_mw": 1064.0,
                "latitude": 26.9157,
                "longitude": 70.9083,
                "elevation_m": 225.0,
                "technology": "1.5MW - 2.1MW Suzlon Wind Turbines",
                "commissioning_year": 2012,
                "operator_name": "Suzlon Energy / Mytrah Energy",
                "region_code": "NR",
                "state_code": "RJ"
            },
            {
                "name": "Charanka Solar Park",
                "code": "CHARANKA_SOLAR_01",
                "plant_type": "solar",
                "capacity_mw": 790.0,
                "latitude": 23.9044,
                "longitude": 71.2023,
                "elevation_m": 12.0,
                "technology": "Crystalline Silicon Fixed Tilt + Seasonal Tilt Arrays",
                "commissioning_year": 2012,
                "operator_name": "Gujarat Power Corporation Ltd (GPCL)",
                "region_code": "WR",
                "state_code": "GJ"
            },
            {
                "name": "Khavda Hybrid Renewable Energy Park",
                "code": "KHAVDA_HYBRID_01",
                "plant_type": "hybrid",
                "capacity_mw": 5000.0,
                "latitude": 23.8500,
                "longitude": 69.7500,
                "elevation_m": 18.0,
                "technology": "Ultra-scale Bifacial Solar + 5.2MW Direct Drive Wind Turbines",
                "commissioning_year": 2024,
                "operator_name": "Adani Green Energy Ltd (AGEL)",
                "region_code": "WR",
                "state_code": "GJ"
            }
        ]

        plant_map = {}
        for p in plants_data:
            existing = db.query(Plant).filter(Plant.code == p["code"]).first()
            if not existing:
                existing = Plant(
                    name=p["name"],
                    code=p["code"],
                    plant_type=p["plant_type"],
                    capacity_mw=p["capacity_mw"],
                    latitude=p["latitude"],
                    longitude=p["longitude"],
                    elevation_m=p["elevation_m"],
                    technology=p["technology"],
                    commissioning_year=p["commissioning_year"],
                    operator_name=p["operator_name"],
                    region_id=region_map[p["region_code"]].id,
                    state_id=state_map[p["state_code"]].id,
                    status="active"
                )
                db.add(existing)
                db.flush()
            plant_map[p["code"]] = existing

        # 4. Hourly Forecast & Weather Data (72-hour Horizon)
        base_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        
        # Check if forecasts already seeded
        forecast_count = db.query(Forecast).count()
        if forecast_count < 100:
            print("[SEED] Generating 72-hour realistic generation forecasts and weather telemetry...")
            for plant_code, plant in plant_map.items():
                is_solar = plant.plant_type in ("solar", "hybrid")
                is_wind = plant.plant_type in ("wind", "hybrid")

                for hour_offset in range(72):
                    target_time = base_time + timedelta(hours=hour_offset)
                    hour_of_day = target_time.hour

                    # Weather Simulation
                    if is_solar:
                        # Solar bell curve: rises at 6am, peaks at 12pm-1pm, sets at 6pm
                        if 6 <= hour_of_day <= 18:
                            rad = math.sin((hour_of_day - 6) / 12.0 * math.pi)
                            ghi = round(max(0.0, rad * 950.0 + (5.0 * (hour_offset % 7))), 1)
                            dni = round(ghi * 0.85, 1)
                            dhi = round(ghi * 0.15, 1)
                            temp = round(28.0 + rad * 12.0, 1)
                            cloud = round(max(0.0, 15.0 + math.cos(hour_offset * 0.3) * 10.0), 1)
                        else:
                            ghi, dni, dhi = 0.0, 0.0, 0.0
                            temp = round(22.0 - ((hour_of_day + 4) % 6) * 0.8, 1)
                            cloud = round(10.0 + (hour_offset % 5), 1)
                    else:
                        ghi, dni, dhi = 0.0, 0.0, 0.0
                        temp = round(26.0 + math.sin(hour_of_day / 24.0 * 2 * math.pi) * 6.0, 1)
                        cloud = round(25.0 + math.sin(hour_offset * 0.5) * 15.0, 1)

                    # Wind simulation: peaks in late afternoon/night
                    wind_diurnal = 7.5 + math.sin((hour_of_day - 14) / 24.0 * 2 * math.pi) * 3.5
                    wind_100m = round(max(2.5, wind_diurnal + (math.sin(hour_offset * 0.8) * 1.8)), 1)
                    wind_10m = round(wind_100m * 0.72, 1)

                    weather_record = Weather(
                        plant_id=plant.id,
                        timestamp=target_time,
                        ghi=ghi,
                        dni=dni,
                        dhi=dhi,
                        temperature_c=temp,
                        relative_humidity=round(45.0 + math.cos(hour_of_day / 12.0) * 15.0, 1),
                        cloud_cover_pct=cloud,
                        surface_pressure_hpa=1010.5,
                        wind_speed_10m=wind_10m,
                        wind_speed_100m=wind_100m,
                        wind_direction_deg=round((240.0 + hour_offset * 2.5) % 360, 1),
                        source="open_meteo"
                    )
                    db.add(weather_record)

                    # Generation Forecast Calculation
                    solar_mw = 0.0
                    wind_mw = 0.0

                    if is_solar:
                        solar_ratio = (ghi / 1000.0) * (1.0 - cloud * 0.005)
                        # Derating from temperature (0.35% per deg C above 25C)
                        temp_derate = max(0.85, 1.0 - max(0.0, temp - 25.0) * 0.0035)
                        solar_cap = plant.capacity_mw * (0.6 if plant.plant_type == "hybrid" else 1.0)
                        solar_mw = max(0.0, solar_cap * solar_ratio * temp_derate)

                    if is_wind:
                        wind_cap = plant.capacity_mw * (0.4 if plant.plant_type == "hybrid" else 1.0)
                        # Power curve logic
                        cut_in, rated, cut_out = 3.0, 11.5, 25.0
                        if wind_100m < cut_in or wind_100m > cut_out:
                            wind_mw = 0.0
                        elif wind_100m >= rated:
                            wind_mw = wind_cap
                        else:
                            wind_mw = wind_cap * ((wind_100m - cut_in) / (rated - cut_in)) ** 2.2

                    total_predicted = round(solar_mw + wind_mw, 1)
                    confidence = round(max(0.82, 0.95 - (hour_offset / 72.0) * 0.12), 2)
                    uncertainty_margin = (1.0 - confidence) * plant.capacity_mw * 0.4
                    lower_bound = round(max(0.0, total_predicted - uncertainty_margin), 1)
                    upper_bound = round(min(plant.capacity_mw, total_predicted + uncertainty_margin), 1)

                    horizon = 24 if hour_offset < 24 else (48 if hour_offset < 48 else 72)

                    forecast_record = Forecast(
                        plant_id=plant.id,
                        forecast_timestamp=target_time,
                        horizon_hours=horizon,
                        predicted_mw=total_predicted,
                        confidence_score=confidence,
                        lower_bound_mw=lower_bound,
                        upper_bound_mw=upper_bound,
                        actual_mw=None,
                        model_version="v1.0-xgb"
                    )
                    db.add(forecast_record)

        # 5. Grid Alerts & Explainable Recommendations
        if db.query(Alert).count() == 0:
            print("[SEED] Populating realistic active grid alerts and operational recommendations...")

            bhadla = plant_map["BHADLA_SOLAR_01"]
            alert_1 = Alert(
                plant_id=bhadla.id,
                alert_type="over_generation",
                severity="critical",
                title="Bhadla Solar Park: Severe Over-Generation Warning (+420 MW)",
                description="Unanticipated high clear-sky irradiance and low ambient aerosol optical depth will drive peak output to 2,180 MW (+420 MW above scheduled dispatch) between 11:00 and 14:00 UTC.",
                start_time=base_time + timedelta(hours=3),
                end_time=base_time + timedelta(hours=6),
                delta_mw=420.0,
                status="active",
                confidence=0.92
            )
            db.add(alert_1)
            db.flush()

            rec_1a = Recommendation(
                alert_id=alert_1.id,
                action_type="storage_charge",
                title="Dispatch Battery Energy Storage Systems (BESS)",
                summary="Command Bhadla substation co-located 300 MW / 600 MWh BESS to absorb 280 MW excess solar generation.",
                rationale="Prevents 765kV green energy corridor line thermal overload while storing low-cost clean power for release during the evening peak demand ramp (19:00 - 22:00 IST).",
                recommended_mw=280.0,
                priority=1,
                estimated_cost_saving_inr=1420000.0
            )
            rec_1b = Recommendation(
                alert_id=alert_1.id,
                action_type="controlled_curtailment",
                title="Order Dynamic Smart Inverter Curtailment",
                summary="Curtail 140 MW across Section 4 inverter blocks if regional transmission line capacity exceeds 94% threshold.",
                rationale="Standard operating protocol to maintain grid frequency below 50.05 Hz statutory ceiling under high solar surge conditions.",
                recommended_mw=140.0,
                priority=2,
                estimated_cost_saving_inr=450000.0
            )
            db.add(rec_1a)
            db.add(rec_1b)

            muppandal = plant_map["MUPPANDAL_WIND_01"]
            alert_2 = Alert(
                plant_id=muppandal.id,
                alert_type="under_generation",
                severity="warning",
                title="Muppandal Wind Farm: Palghat Gap Wind Deficit (-210 MW)",
                description="Sudden wind speed drop from 11.2 m/s down to 4.8 m/s anticipated across Kanyakumari/Tirunelveli wind corridor between 18:00 and 22:00 UTC.",
                start_time=base_time + timedelta(hours=10),
                end_time=base_time + timedelta(hours=14),
                delta_mw=210.0,
                status="active",
                confidence=0.88
            )
            db.add(alert_2)
            db.flush()

            rec_2a = Recommendation(
                alert_id=alert_2.id,
                action_type="backup_dispatch",
                title="Fast-Ramping Hydro Reserve Activation",
                summary="Instruct Kadamparai 400 MW Pumped Storage Hydro generation to dispatch 150 MW within 15 minutes.",
                rationale="Immediate black-start/fast-response capability prevents Southern Regional grid frequency dip below 49.90 Hz during peak industrial draw.",
                recommended_mw=150.0,
                priority=1,
                estimated_cost_saving_inr=890000.0
            )
            rec_2b = Recommendation(
                alert_id=alert_2.id,
                action_type="power_procurement",
                title="Procure Ancillary Power on Real-Time Market (RTM)",
                summary="Execute 60 MW purchase order on Indian Energy Exchange (IEX) RTM window.",
                rationale="Hedging the remaining deficit through bilateral RTM minimizes deviation settlement mechanism (DSM) penalty charges.",
                recommended_mw=60.0,
                priority=2,
                estimated_cost_saving_inr=320000.0
            )
            db.add(rec_2a)
            db.add(rec_2b)

            pavagada = plant_map["PAVAGADA_SOLAR_01"]
            alert_3 = Alert(
                plant_id=pavagada.id,
                alert_type="ramp_warning",
                severity="critical",
                title="Pavagada Solar Park: Rapid Cloud Ramp-Down (-380 MW/hr)",
                description="Fast-moving convective cloud cell approaching Tumakuru district will trigger steep generation decline exceeding 380 MW/hr at 15:00 UTC.",
                start_time=base_time + timedelta(hours=7),
                end_time=base_time + timedelta(hours=9),
                delta_mw=380.0,
                status="active",
                confidence=0.85
            )
            db.add(alert_3)
            db.flush()

            rec_3a = Recommendation(
                alert_id=alert_3.id,
                action_type="storage_discharge",
                title="Discharge Microgrid Energy Storage Buffer",
                summary="Pre-arm local 100 MW BESS for automatic frequency support injection upon ramp rate detection > 5 MW/sec.",
                rationale="Instantaneous synthetic inertia and MW ramp compensation stabilizes local 400kV bus voltage.",
                recommended_mw=100.0,
                priority=1,
                estimated_cost_saving_inr=650000.0
            )
            db.add(rec_3a)

        # 6. Model Run Registry
        if db.query(ModelRun).count() == 0:
            solar_run = ModelRun(
                model_name="solar_xgboost_ensemble",
                model_type="solar",
                version="v1.0.0-solar-xgb",
                mae_mw=18.4,
                rmse_mw=27.2,
                r2_score=0.942,
                parameters='{"n_estimators": 350, "max_depth": 6, "learning_rate": 0.05, "subsample": 0.85}',
                feature_importance='{"ghi": 0.46, "dni": 0.22, "temperature_c": 0.14, "cloud_cover_pct": 0.11, "hour_of_day": 0.07}',
                model_path="trained_models/solar_xgboost_v1.joblib",
                is_active=True
            )
            wind_run = ModelRun(
                model_name="wind_xgboost_ensemble",
                model_type="wind",
                version="v1.0.0-wind-xgb",
                mae_mw=24.8,
                rmse_mw=38.6,
                r2_score=0.918,
                parameters='{"n_estimators": 400, "max_depth": 7, "learning_rate": 0.04, "subsample": 0.80}',
                feature_importance='{"wind_speed_100m": 0.58, "wind_speed_10m": 0.18, "wind_direction_deg": 0.12, "surface_pressure_hpa": 0.07, "temperature_c": 0.05}',
                model_path="trained_models/wind_xgboost_v1.joblib",
                is_active=True
            )
            db.add(solar_run)
            db.add(wind_run)

        # Commit all seeded data
        db.commit()
        print("[SUCCESS] Database successfully seeded with regions, plants, weather, 72h forecasts, alerts, and models!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
