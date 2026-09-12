import os
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import xgboost as xgb
from sqlalchemy.orm import Session

from app.models.plant import Plant
from app.models.weather import Weather
from app.data_pipeline.metadata_manager import PlantMetadataManager
from app.ml.features import FeatureEngineer
from app.ml.solar_model import SolarForecaster
from app.ml.wind_model import WindForecaster
from app.services.forecast_engine import forecast_engine

logger = logging.getLogger("backend.explainability.explainer")

# -----------------------------------------------------------------------------
# DOMAIN METADATA & CATEGORIZATION
# -----------------------------------------------------------------------------
SOLAR_FEATURE_META = {
    "ghi": ("solar_radiation", "Global Horizontal Irradiance", "Surface total solar radiation intensity (W/m^2)"),
    "dni": ("solar_radiation", "Direct Normal Irradiance", "Direct solar beam intensity perpendicular to rays (W/m^2)"),
    "dhi": ("solar_radiation", "Diffuse Horizontal Irradiance", "Scattered diffuse sky radiation (W/m^2)"),
    "clear_sky_ghi": ("solar_radiation", "Clear Sky GHI", "Theoretical maximum cloudless GHI (W/m^2)"),
    "clear_sky_dni": ("solar_radiation", "Clear Sky DNI", "Theoretical maximum cloudless direct beam (W/m^2)"),
    "clearness_index": ("cloud_cover", "Clearness Index (kt)", "Atmospheric transmission ratio (GHI / extraterrestrial)"),
    "diffuse_ratio": ("solar_radiation", "Diffuse Fraction", "Ratio of scattered diffuse radiation to total GHI"),
    "cloud_cover_pct": ("cloud_cover", "Cloud Cover", "Total sky cloud coverage fraction (%)"),
    "cloud_attenuation_factor": ("cloud_cover", "Cloud Attenuation", "Non-linear optical extinction of solar photons"),
    "solar_elevation_deg": ("celestial_geometry", "Solar Elevation Angle", "Altitude angle of the sun above the horizon (deg)"),
    "solar_zenith_deg": ("celestial_geometry", "Solar Zenith Angle", "Angular distance of sun from vertical zenith (deg)"),
    "solar_azimuth_deg": ("celestial_geometry", "Solar Azimuth Angle", "Compass orientation of the sun (deg)"),
    "air_mass": ("celestial_geometry", "Optical Air Mass", "Atmospheric path length traversed by sunlight"),
    "cosine_zenith": ("celestial_geometry", "Cosine Zenith Factor", "Geometric projection factor of sunlight on earth"),
    "temperature_c": ("ambient_thermal", "Ambient Temperature", "Dry-bulb ambient air temperature (deg C)"),
    "cell_temperature_c": ("ambient_thermal", "PV Cell Temperature", "Internal operating junction temperature of PV cells"),
    "thermal_loss_factor": ("ambient_thermal", "Thermal Derating Factor", "Efficiency degradation per degree above 25 deg C STC"),
    "relative_humidity": ("ambient_thermal", "Relative Humidity", "Atmospheric water vapor saturation fraction (%)"),
    "surface_pressure_hpa": ("ambient_thermal", "Surface Barometric Pressure", "Atmospheric barometric pressure (hPa)"),
    "hour_sin": ("temporal_dynamics", "Hour Diurnal Cycle (Sin)", "Cyclical cyclical representation of solar noon"),
    "hour_cos": ("temporal_dynamics", "Hour Diurnal Cycle (Cos)", "Cyclical 24-hour diurnal phase"),
    "day_of_year_sin": ("temporal_dynamics", "Seasonal Orbit (Sin)", "Earth orbit eccentricity cyclical factor"),
    "day_of_year_cos": ("temporal_dynamics", "Seasonal Orbit (Cos)", "Annual solar declination cycle"),
    "ghi_lag_1h": ("temporal_dynamics", "GHI 1h Lag", "Solar radiation persistent baseline 1 hour prior"),
    "ghi_lag_2h": ("temporal_dynamics", "GHI 2h Lag", "Solar radiation persistent baseline 2 hours prior"),
    "ghi_rolling_mean_3h": ("temporal_dynamics", "3h Solar Trend", "3-hour moving average of solar radiation"),
    "ghi_rolling_std_3h": ("temporal_dynamics", "Solar Volatility", "3-hour moving standard deviation (cloud ramp turbulence)"),
    "morning_ramp": ("temporal_dynamics", "Morning Sunrise Ramp", "Rapid dawn generation transition flag"),
    "evening_ramp": ("temporal_dynamics", "Evening Sunset Ramp", "Rapid dusk generation ramp down flag"),
    "capacity_mw": ("plant_hardware", "Nameplate Capacity", "Total peak DC/AC rated park capacity (MW)"),
    "elevation_m": ("plant_hardware", "Altitude Elevation", "Plant elevation above sea level (meters)"),
    "panel_efficiency": ("plant_hardware", "Module Efficiency", "Nameplate photoelectric conversion efficiency (%)"),
    "inverter_efficiency": ("plant_hardware", "Inverter Efficiency", "DC to AC conversion efficiency (%)"),
    "tracker_gain_factor": ("plant_hardware", "Tracker Gain Factor", "Yield multiplier from single/dual-axis trackers")
}

WIND_FEATURE_META = {
    "wind_speed_100m": ("wind_resource", "100m Hub-Height Wind Speed", "Velocity of wind at turbine rotor centerline (m/s)"),
    "wind_speed_10m": ("wind_resource", "10m Reference Wind Speed", "Near-surface anemometer wind speed (m/s)"),
    "wind_cubic": ("wind_resource", "Cubic Wind Power Potential (v^3)", "Kinetic power flux proportional to velocity cubed"),
    "wind_power_density": ("wind_resource", "Wind Power Density (W/m^2)", "Available kinetic energy per square meter of swept rotor"),
    "air_density_kg_m3": ("air_density_aerodynamics", "Atmospheric Air Density", "Moist air mass density per cubic meter (kg/m^3)"),
    "temperature_c": ("air_density_aerodynamics", "Ambient Temperature", "Dry-bulb ambient air temperature (deg C)"),
    "surface_pressure_hpa": ("air_density_aerodynamics", "Barometric Pressure", "Surface atmospheric pressure affecting air density"),
    "relative_humidity": ("air_density_aerodynamics", "Relative Humidity", "Moisture vapor pressure fraction"),
    "wind_shear_alpha": ("wind_shear_turbulence", "Wind Shear Exponent (Hellmann)", "Vertical wind speed gradient between 10m and 100m"),
    "gust_factor": ("wind_shear_turbulence", "Gust Speed Ratio", "Peak gust speed relative to mean hourly velocity"),
    "turbulence_intensity": ("wind_shear_turbulence", "Turbulence Intensity", "Velocity standard deviation over mean wind speed"),
    "wind_direction_deg": ("directional_alignment", "Wind Direction", "Compass bearing of incoming wind flow (deg)"),
    "wind_direction_sin": ("directional_alignment", "Wind Direction (Sin)", "Harmonic East-West vector component"),
    "wind_direction_cos": ("directional_alignment", "Wind Direction (Cos)", "Harmonic North-South vector component"),
    "direction_alignment": ("directional_alignment", "Rotor Alignment Ratio", "Aerodynamic alignment with dominant wind rose angle"),
    "hour_sin": ("temporal_dynamics", "Diurnal Cycle (Sin)", "Diurnal atmospheric boundary layer oscillation"),
    "hour_cos": ("temporal_dynamics", "Diurnal Cycle (Cos)", "Diurnal thermal inversion phase"),
    "day_of_year_sin": ("temporal_dynamics", "Seasonal Monsoon (Sin)", "Seasonal monsoon and trade wind cycle"),
    "day_of_year_cos": ("temporal_dynamics", "Seasonal Monsoon (Cos)", "Annual seasonal thermal gradient cycle"),
    "wind_speed_lag_1h": ("temporal_dynamics", "Wind Speed 1h Lag", "Wind velocity persistent baseline 1 hour prior"),
    "wind_speed_lag_2h": ("temporal_dynamics", "Wind Speed 2h Lag", "Wind velocity persistent baseline 2 hours prior"),
    "wind_rolling_mean_3h": ("temporal_dynamics", "3h Wind Trend", "3-hour moving average of wind velocity"),
    "wind_rolling_std_3h": ("temporal_dynamics", "Wind Volatility", "3-hour moving standard deviation of wind"),
    "capacity_mw": ("turbine_specs", "Total Wind Farm Capacity", "Aggregated nameplate capacity of wind park (MW)"),
    "hub_height_m": ("turbine_specs", "Turbine Hub Height", "Centerline elevation of turbine nacelle (meters)"),
    "rotor_diameter_m": ("turbine_specs", "Rotor Diameter", "Swept blade circle diameter (meters)"),
    "cut_in_speed_m_s": ("turbine_specs", "Cut-in Wind Speed", "Minimum threshold velocity for power generation (3.0 m/s)"),
    "rated_speed_m_s": ("turbine_specs", "Rated Wind Speed", "Velocity at which turbine reaches nameplate output (12.0 m/s)"),
    "cut_out_speed_m_s": ("turbine_specs", "Cut-out Storm Trip Speed", "Emergency high-wind brake shutdown threshold (25.0 m/s)"),
    "power_coefficient_cp": ("turbine_specs", "Aerodynamic Cp Coefficient", "Betz limit aerodynamic power conversion efficiency")
}

CATEGORY_NAMES = {
    "solar_radiation": "Solar Irradiance (GHI / DNI / DHI)",
    "celestial_geometry": "Celestial Geometry & Sun Angles",
    "cloud_cover": "Cloud Cover & Optical Attenuation",
    "ambient_thermal": "Ambient Temperature & Thermal Derating",
    "temporal_dynamics": "Temporal Dynamics & Inertial Lags",
    "plant_hardware": "Facility Hardware & Tracker Geometry",
    "wind_resource": "Hub-Height Wind Speed & Kinetic Power",
    "air_density_aerodynamics": "Air Density & Barometric Aerodynamics",
    "directional_alignment": "Wind Direction & Rotor Yaw Alignment",
    "wind_shear_turbulence": "Wind Shear Gradient & Turbulence",
    "turbine_specs": "Turbine Specifications & Power Curve Limits"
}

class ExplainabilityEngine:
    """
    Production-grade Explainability Engine for Renewable Generation Forecasting.
    Features:
      1. Global Feature Importance (Gain, Weight, Cover)
      2. TreeSHAP Waterfall (Exact additive local contributions)
      3. Physical Weather Driver Breakdown
      4. Meteorological Sensitivity & Elasticity Curves
    """

    def __init__(self):
        self.forecast_service = forecast_engine

    # -------------------------------------------------------------------------
    # 1. GLOBAL FEATURE IMPORTANCE
    # -------------------------------------------------------------------------
    def get_global_feature_importance(
        self,
        model_type: str = "solar"
    ) -> Dict[str, Any]:
        """
        Extract global feature importance metrics (gain, weight, cover) from trained XGBoost model.
        """
        model_type = model_type.lower()
        if model_type not in ["solar", "wind", "hybrid"]:
            raise ValueError(f"Unsupported model type: {model_type}. Must be 'solar', 'wind', or 'hybrid'.")

        if model_type == "solar":
            forecaster = self.forecast_service._get_solar_forecaster()
            booster = forecaster.model.get_booster()
            meta_dict = SOLAR_FEATURE_META
            version = "v1.0.0-solar-xgb"
            fn_list = forecaster.feature_names
        elif model_type == "wind":
            forecaster = self.forecast_service._get_wind_forecaster()
            booster = forecaster.model.get_booster()
            meta_dict = WIND_FEATURE_META
            version = "v1.0.0-wind-xgb"
            fn_list = forecaster.feature_names
        else:  # hybrid
            # Weighted mix of solar and wind models
            solar_res = self.get_global_feature_importance("solar")
            wind_res = self.get_global_feature_importance("wind")
            combined_features = []
            for f in solar_res["top_features"]:
                f_copy = dict(f)
                f_copy["importance_score"] = round(f_copy["importance_score"] * 0.6, 4)
                f_copy["percentage"] = round(f_copy["percentage"] * 0.6, 2)
                combined_features.append(f_copy)
            for f in wind_res["top_features"]:
                f_copy = dict(f)
                f_copy["importance_score"] = round(f_copy["importance_score"] * 0.4, 4)
                f_copy["percentage"] = round(f_copy["percentage"] * 0.4, 2)
                combined_features.append(f_copy)

            combined_features.sort(key=lambda x: x["importance_score"], reverse=True)
            for r, f in enumerate(combined_features, 1):
                f["rank"] = r

            cat_imp: Dict[str, float] = {}
            for f in combined_features:
                cat_imp[f["category"]] = round(cat_imp.get(f["category"], 0.0) + f["percentage"], 2)

            return {
                "model_type": "hybrid",
                "model_version": "v1.0.0-hybrid-ensemble",
                "total_features": len(combined_features),
                "top_features": combined_features,
                "category_importance": cat_imp
            }

        # Query scores from booster
        gain_scores = booster.get_score(importance_type="gain")
        weight_scores = booster.get_score(importance_type="weight")
        cover_scores = booster.get_score(importance_type="cover")

        total_gain = sum(gain_scores.values()) if gain_scores else 1.0

        feature_items = []
        for feat in fn_list:
            gain = float(gain_scores.get(feat, 0.0))
            weight = float(weight_scores.get(feat, 0.0))
            cover = float(cover_scores.get(feat, 0.0))
            pct = round((gain / total_gain) * 100.0, 2)

            cat, disp_name, desc = meta_dict.get(
                feat,
                ("general", feat.replace("_", " ").title(), f"Engineered feature {feat}")
            )

            feature_items.append({
                "feature_name": feat,
                "importance_score": round(gain, 4),
                "weight": weight,
                "cover": cover,
                "percentage": pct,
                "rank": 0,
                "category": cat,
                "description": desc
            })

        # Sort by gain descending
        feature_items.sort(key=lambda x: x["importance_score"], reverse=True)
        for rank, item in enumerate(feature_items, 1):
            item["rank"] = rank

        # Category level aggregation
        cat_imp: Dict[str, float] = {}
        for item in feature_items:
            c = item["category"]
            cat_imp[c] = round(cat_imp.get(c, 0.0) + item["percentage"], 2)

        return {
            "model_type": model_type,
            "model_version": version,
            "total_features": len(feature_items),
            "top_features": feature_items,
            "category_importance": cat_imp
        }

    # -------------------------------------------------------------------------
    # 2. SHAP WATERFALL (Local Attribution)
    # -------------------------------------------------------------------------
    def compute_shap_waterfall(
        self,
        db: Session,
        plant_id: int,
        horizon_hour: int = 12
    ) -> Dict[str, Any]:
        """
        Compute exact TreeSHAP waterfall local feature attribution for a specific forecast hour.
        Base value + Sum(SHAP_i) = Model Prediction.
        """
        plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            raise ValueError(f"Plant with ID {plant_id} does not exist.")

        metadata = PlantMetadataManager.get_plant_metadata(db, plant_id)
        capacity_mw = float(plant.capacity_mw)
        plant_type = plant.plant_type.lower()

        # Ensure weather data
        weather_data = self.forecast_service._ensure_weather_data(db, plant, max(24, horizon_hour + 1))
        df_weather = pd.DataFrame(weather_data)
        if len(df_weather) <= horizon_hour:
            horizon_hour = max(0, len(df_weather) - 1)

        target_ts = df_weather["timestamp"].iloc[horizon_hour]
        X_solar, X_wind = FeatureEngineer.create_feature_matrix(df_weather, metadata)

        if plant_type == "solar":
            forecaster = self.forecast_service._get_solar_forecaster()
            booster = forecaster.model.get_booster()
            fn = forecaster.feature_names
            row_vals = X_solar.iloc[horizon_hour:horizon_hour+1]
            dmat = xgb.DMatrix(row_vals, feature_names=fn)
            contribs = booster.predict(dmat, pred_contribs=True)[0]
            base_val = float(contribs[-1])
            shap_vals = contribs[:-1]
            meta_dict = SOLAR_FEATURE_META

        elif plant_type == "wind":
            forecaster = self.forecast_service._get_wind_forecaster()
            booster = forecaster.model.get_booster()
            fn = forecaster.feature_names
            row_vals = X_wind.iloc[horizon_hour:horizon_hour+1]
            dmat = xgb.DMatrix(row_vals, feature_names=fn)
            contribs = booster.predict(dmat, pred_contribs=True)[0]
            base_val = float(contribs[-1])
            shap_vals = contribs[:-1]
            meta_dict = WIND_FEATURE_META

        else:  # hybrid
            # Weighted combination of solar (60%) and wind (40%)
            solar_fc = self.forecast_service._get_solar_forecaster()
            wind_fc = self.forecast_service._get_wind_forecaster()

            s_booster = solar_fc.model.get_booster()
            w_booster = wind_fc.model.get_booster()

            s_contribs = s_booster.predict(xgb.DMatrix(X_solar.iloc[horizon_hour:horizon_hour+1], feature_names=solar_fc.feature_names), pred_contribs=True)[0]
            w_contribs = w_booster.predict(xgb.DMatrix(X_wind.iloc[horizon_hour:horizon_hour+1], feature_names=wind_fc.feature_names), pred_contribs=True)[0]

            base_val = float(0.6 * s_contribs[-1] + 0.4 * w_contribs[-1])
            meta_dict = {**SOLAR_FEATURE_META, **WIND_FEATURE_META}

            # Merge features
            combined_dict = {}
            for name, val, f_val in zip(solar_fc.feature_names, s_contribs[:-1], X_solar.iloc[horizon_hour]):
                combined_dict[f"solar_{name}"] = (float(val * 0.6), float(f_val), SOLAR_FEATURE_META.get(name, ("solar", name, "")))
            for name, val, f_val in zip(wind_fc.feature_names, w_contribs[:-1], X_wind.iloc[horizon_hour]):
                combined_dict[f"wind_{name}"] = (float(val * 0.4), float(f_val), WIND_FEATURE_META.get(name, ("wind", name, "")))

            fn = list(combined_dict.keys())
            shap_vals = [combined_dict[k][0] for k in fn]
            row_vals = pd.DataFrame([{k: combined_dict[k][1] for k in fn}])

        # Build waterfall list
        waterfall_raw = []
        for i, f_name in enumerate(fn):
            s_val = float(shap_vals[i])
            f_val = float(row_vals.iloc[0][f_name]) if isinstance(row_vals, pd.DataFrame) else float(row_vals[f_name])

            if f_name in meta_dict:
                cat, disp, desc = meta_dict[f_name]
            elif f_name.startswith("solar_") and f_name[6:] in SOLAR_FEATURE_META:
                cat, disp, desc = SOLAR_FEATURE_META[f_name[6:]]
                disp = f"Solar {disp}"
            elif f_name.startswith("wind_") and f_name[5:] in WIND_FEATURE_META:
                cat, disp, desc = WIND_FEATURE_META[f_name[5:]]
                disp = f"Wind {disp}"
            else:
                cat = "general"
                disp = f_name.replace("_", " ").title()

            waterfall_raw.append({
                "feature_name": f_name,
                "display_name": disp,
                "category": cat,
                "feature_value": round(f_val, 3),
                "shap_value": round(s_val, 3),
                "abs_shap": abs(s_val),
                "direction": "positive" if s_val >= 0 else "negative"
            })

        # Sort by absolute SHAP impact
        waterfall_raw.sort(key=lambda x: x["abs_shap"], reverse=True)

        # Cumulative step progression
        cum = base_val
        waterfall_steps = []
        for item in waterfall_raw:
            cum += item["shap_value"]
            waterfall_steps.append({
                "feature_name": item["feature_name"],
                "display_name": item["display_name"],
                "category": item["category"],
                "feature_value": item["feature_value"],
                "shap_value": item["shap_value"],
                "cumulative_value": round(cum, 3),
                "direction": item["direction"]
            })

        pred_mw = max(0.0, min(capacity_mw, cum))

        # Separate top positives and negatives
        positives = [w for w in waterfall_steps if w["direction"] == "positive"]
        negatives = [w for w in waterfall_steps if w["direction"] == "negative"]

        positives.sort(key=lambda x: x["shap_value"], reverse=True)
        negatives.sort(key=lambda x: x["shap_value"])  # most negative first

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "timestamp": target_ts,
            "base_value": round(base_val, 2),
            "predicted_mw": round(pred_mw, 2),
            "unit": "MW",
            "waterfall_steps": waterfall_steps,
            "top_positive_features": positives[:10],
            "top_negative_features": negatives[:10]
        }

    # -------------------------------------------------------------------------
    # 3. PHYSICAL WEATHER DRIVER BREAKDOWN
    # -------------------------------------------------------------------------
    def get_driver_breakdown(
        self,
        db: Session,
        plant_id: int,
        horizon_hour: int = 12
    ) -> Dict[str, Any]:
        """
        Aggregate SHAP values into human-interpretable meteorological driver categories.
        """
        waterfall_res = self.compute_shap_waterfall(db, plant_id, horizon_hour)

        cat_impacts: Dict[str, Dict[str, Any]] = {}
        for step in waterfall_res["waterfall_steps"]:
            c = step["category"]
            if c not in cat_impacts:
                cat_impacts[c] = {
                    "category_id": c,
                    "category_name": CATEGORY_NAMES.get(c, c.replace("_", " ").title()),
                    "impact_mw": 0.0,
                    "features": []
                }
            cat_impacts[c]["impact_mw"] += step["shap_value"]
            cat_impacts[c]["features"].append(step["display_name"])

        total_abs_impact = sum(abs(v["impact_mw"]) for v in cat_impacts.values())
        if total_abs_impact == 0:
            total_abs_impact = 1.0

        drivers_list = []
        for c, data in cat_impacts.items():
            impact = round(data["impact_mw"], 2)
            pct = round((abs(impact) / total_abs_impact) * 100.0, 2)
            direction = "positive" if impact >= 0 else "negative"

            if c == "solar_radiation":
                desc = f"Direct & diffuse sunlight contributed {impact:+.1f} MW relative to average baseline."
            elif c == "cloud_cover":
                desc = f"Cloud cover and atmospheric attenuation caused {impact:+.1f} MW swing."
            elif c == "ambient_thermal":
                desc = f"Ambient temperature and cell thermal derating altered output by {impact:+.1f} MW."
            elif c == "wind_resource":
                desc = f"Hub-height kinetic wind velocity drove {impact:+.1f} MW change in turbine rotor output."
            elif c == "air_density_aerodynamics":
                desc = f"Atmospheric air density aerodynamic factor contributed {impact:+.1f} MW."
            elif c == "celestial_geometry":
                desc = f"Solar elevation angle and zenith projection contributed {impact:+.1f} MW."
            else:
                desc = f"Dynamic atmospheric and operational factors contributed {impact:+.1f} MW."

            drivers_list.append({
                "category_id": c,
                "category_name": data["category_name"],
                "impact_mw": impact,
                "percentage_impact": pct,
                "direction": direction,
                "description": desc,
                "key_features": data["features"][:5]
            })

        drivers_list.sort(key=lambda x: abs(x["impact_mw"]), reverse=True)
        net_impact = sum(d["impact_mw"] for d in drivers_list)

        return {
            "plant_id": waterfall_res["plant_id"],
            "plant_name": waterfall_res["plant_name"],
            "plant_type": waterfall_res["plant_type"],
            "timestamp": waterfall_res["timestamp"],
            "predicted_mw": waterfall_res["predicted_mw"],
            "base_value": waterfall_res["base_value"],
            "net_weather_impact_mw": round(net_impact, 2),
            "drivers": drivers_list
        }

    # -------------------------------------------------------------------------
    # 4. METEOROLOGICAL SENSITIVITY ANALYSIS
    # -------------------------------------------------------------------------
    def compute_meteorological_sensitivity(
        self,
        db: Session,
        plant_id: int,
        parameter: str = "ghi",
        variation_range: Optional[List[float]] = None,
        horizon_hour: int = 12
    ) -> Dict[str, Any]:
        """
        Compute partial sensitivity curve and generation elasticity for weather variations.
        """
        plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            raise ValueError(f"Plant with ID {plant_id} does not exist.")

        metadata = PlantMetadataManager.get_plant_metadata(db, plant_id)
        capacity_mw = float(plant.capacity_mw)
        plant_type = plant.plant_type.lower()

        weather_data = self.forecast_service._ensure_weather_data(db, plant, max(24, horizon_hour + 1))
        df_weather = pd.DataFrame(weather_data)
        if len(df_weather) <= horizon_hour:
            horizon_hour = max(0, len(df_weather) - 1)

        param = parameter.lower().strip()
        base_row = df_weather.iloc[horizon_hour].to_dict()

        # Baseline prediction
        X_s, X_w = FeatureEngineer.create_feature_matrix(pd.DataFrame([base_row]), metadata)
        if plant_type == "solar":
            base_pred = float(self.forecast_service._get_solar_forecaster().predict(X_s)[0])
        elif plant_type == "wind":
            base_pred = float(self.forecast_service._get_wind_forecaster().predict(X_w)[0])
        else:
            p_s = float(self.forecast_service._get_solar_forecaster().predict(X_s)[0]) * 0.6
            p_w = float(self.forecast_service._get_wind_forecaster().predict(X_w)[0]) * 0.4
            base_pred = p_s + p_w

        # Configure parameter variations
        if param in ["ghi", "solar_radiation", "irradiance"]:
            unit = "W/m^2"
            base_val = float(base_row.get("ghi", 600.0))
            if variation_range is None:
                variation_range = [-0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.30]
            sim_points = []
            for delta_pct in variation_range:
                val = max(0.0, base_val * (1.0 + delta_pct))
                sim_row = dict(base_row)
                sim_row["ghi"] = val
                sim_row["dni"] = max(0.0, float(base_row.get("dni", 500.0)) * (1.0 + delta_pct))
                sim_row["dhi"] = max(0.0, float(base_row.get("dhi", 100.0)) * (1.0 + delta_pct))
                X_s_sim, _ = FeatureEngineer.create_feature_matrix(pd.DataFrame([sim_row]), metadata)
                if plant_type == "solar":
                    pred = float(self.forecast_service._get_solar_forecaster().predict(X_s_sim)[0])
                elif plant_type == "hybrid":
                    pred = float(self.forecast_service._get_solar_forecaster().predict(X_s_sim)[0]) * 0.6 + (base_pred * 0.4)
                else:
                    pred = base_pred

                mw_delta = pred - base_pred
                pct_change = (mw_delta / base_pred * 100.0) if base_pred > 0 else 0.0
                sim_points.append({
                    "delta_pct": round(delta_pct * 100.0, 1),
                    "delta_value": round(val - base_val, 1),
                    "parameter_value": round(val, 1),
                    "predicted_mw": round(pred, 2),
                    "mw_delta": round(mw_delta, 2),
                    "pct_mw_change": round(pct_change, 2)
                })

        elif param in ["wind_speed", "wind"]:
            unit = "m/s"
            base_val = float(base_row.get("wind_speed_100m", 8.0))
            if variation_range is None:
                variation_range = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
            sim_points = []
            for delta_v in variation_range:
                val = max(0.0, base_val + delta_v)
                delta_pct = (delta_v / base_val * 100.0) if base_val > 0 else 0.0
                sim_row = dict(base_row)
                sim_row["wind_speed_100m"] = val
                sim_row["wind_speed_10m"] = max(0.0, float(base_row.get("wind_speed_10m", 5.0)) + delta_v * 0.7)
                _, X_w_sim = FeatureEngineer.create_feature_matrix(pd.DataFrame([sim_row]), metadata)
                if plant_type == "wind":
                    pred = float(self.forecast_service._get_wind_forecaster().predict(X_w_sim)[0])
                elif plant_type == "hybrid":
                    pred = (base_pred * 0.6) + float(self.forecast_service._get_wind_forecaster().predict(X_w_sim)[0]) * 0.4
                else:
                    pred = base_pred

                mw_delta = pred - base_pred
                pct_change = (mw_delta / base_pred * 100.0) if base_pred > 0 else 0.0
                sim_points.append({
                    "delta_pct": round(delta_pct, 1),
                    "delta_value": round(delta_v, 2),
                    "parameter_value": round(val, 2),
                    "predicted_mw": round(pred, 2),
                    "mw_delta": round(mw_delta, 2),
                    "pct_mw_change": round(pct_change, 2)
                })

        elif param in ["cloud_cover", "clouds"]:
            unit = "%"
            base_val = float(base_row.get("cloud_cover_pct", 20.0))
            if variation_range is None:
                variation_range = [-20.0, -10.0, 0.0, 10.0, 25.0, 50.0]
            sim_points = []
            for delta_c in variation_range:
                val = max(0.0, min(100.0, base_val + delta_c))
                sim_row = dict(base_row)
                sim_row["cloud_cover_pct"] = val
                # Cloud attenuation also affects GHI
                cloud_factor = (1.0 - (val / 100.0) * 0.75)
                sim_row["ghi"] = float(base_row.get("ghi", 600.0)) * cloud_factor
                X_s_sim, _ = FeatureEngineer.create_feature_matrix(pd.DataFrame([sim_row]), metadata)
                if plant_type == "solar":
                    pred = float(self.forecast_service._get_solar_forecaster().predict(X_s_sim)[0])
                elif plant_type == "hybrid":
                    pred = float(self.forecast_service._get_solar_forecaster().predict(X_s_sim)[0]) * 0.6 + (base_pred * 0.4)
                else:
                    pred = base_pred

                mw_delta = pred - base_pred
                pct_change = (mw_delta / base_pred * 100.0) if base_pred > 0 else 0.0
                sim_points.append({
                    "delta_pct": round((delta_c / base_val * 100.0), 1) if base_val > 0 else 0.0,
                    "delta_value": round(delta_c, 1),
                    "parameter_value": round(val, 1),
                    "predicted_mw": round(pred, 2),
                    "mw_delta": round(mw_delta, 2),
                    "pct_mw_change": round(pct_change, 2)
                })

        elif param in ["temperature", "temp"]:
            unit = "deg C"
            base_val = float(base_row.get("temperature_c", 30.0))
            if variation_range is None:
                variation_range = [-5.0, 0.0, 2.0, 5.0, 10.0]
            sim_points = []
            for delta_t in variation_range:
                val = base_val + delta_t
                sim_row = dict(base_row)
                sim_row["temperature_c"] = val
                X_s_sim, X_w_sim = FeatureEngineer.create_feature_matrix(pd.DataFrame([sim_row]), metadata)
                if plant_type == "solar":
                    pred = float(self.forecast_service._get_solar_forecaster().predict(X_s_sim)[0])
                elif plant_type == "wind":
                    pred = float(self.forecast_service._get_wind_forecaster().predict(X_w_sim)[0])
                else:
                    pred = float(self.forecast_service._get_solar_forecaster().predict(X_s_sim)[0]) * 0.6 + \
                           float(self.forecast_service._get_wind_forecaster().predict(X_w_sim)[0]) * 0.4

                mw_delta = pred - base_pred
                pct_change = (mw_delta / base_pred * 100.0) if base_pred > 0 else 0.0
                sim_points.append({
                    "delta_pct": round((delta_t / base_val * 100.0), 1) if base_val > 0 else 0.0,
                    "delta_value": round(delta_t, 1),
                    "parameter_value": round(val, 1),
                    "predicted_mw": round(pred, 2),
                    "mw_delta": round(mw_delta, 2),
                    "pct_mw_change": round(pct_change, 2)
                })
        else:
            raise ValueError(f"Unsupported sensitivity parameter: '{parameter}'. Supported: 'ghi', 'wind_speed', 'cloud_cover', 'temperature'.")

        # Compute elasticity: % dMW / % dParam near baseline
        non_zero_steps = [p for p in sim_points if abs(p.get("delta_value", 0.0)) > 1e-4]
        if non_zero_steps and base_pred > 0:
            closest_step = min(non_zero_steps, key=lambda p: abs(p["delta_value"]))
            denom = closest_step["delta_pct"] if closest_step["delta_pct"] != 0 else 1.0
            elasticity = round(float(closest_step["pct_mw_change"] / denom), 3)
            marginal_rate = round(float(closest_step["mw_delta"] / closest_step["delta_value"]), 3)
        elif non_zero_steps:
            closest_step = min(non_zero_steps, key=lambda p: abs(p["delta_value"]))
            elasticity = 0.0
            marginal_rate = round(float(closest_step["mw_delta"] / closest_step["delta_value"]), 3)
        else:
            elasticity = 0.0
            marginal_rate = 0.0

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "parameter": parameter.upper(),
            "unit": unit,
            "baseline_parameter_value": round(base_val, 2),
            "baseline_predicted_mw": round(base_pred, 2),
            "elasticity": elasticity,
            "marginal_rate_mw_per_unit": marginal_rate,
            "curve": sim_points
        }

# Singleton instance
explainability_engine = ExplainabilityEngine()
