import logging
from typing import Dict, Any, List, Optional, Union
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.plant import Plant
from app.models.region_state import Region, State
from app.services.forecast_engine import forecast_engine

logger = logging.getLogger("backend.aggregation.engine")

class AggregationEngine:
    """
    Production-grade multi-level hierarchical generation forecast aggregation engine.
    Supports bottom-up aggregation across:
      1. Farm (Individual solar/wind/hybrid plant)
      2. Region (NR, WR, SR, ER, NER)
      3. State (RJ, GJ, TN, KA, MH, AP, MP)
      4. National (All-India Renewable Grid)
    Ensures mathematical conservation: Sum(Farms) = Region/State = National.
    """

    def __init__(self):
        self.forecast_service = forecast_engine

    # -------------------------------------------------------------------------
    # 1. FARM LEVEL AGGREGATION
    # -------------------------------------------------------------------------
    def aggregate_farm(
        self,
        db: Session,
        plant_id_or_code: Union[int, str],
        horizon_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Aggregate and enrich generation forecast for an individual renewable facility.
        """
        if isinstance(plant_id_or_code, int) or (isinstance(plant_id_or_code, str) and plant_id_or_code.isdigit()):
            plant = db.query(Plant).filter(Plant.id == int(plant_id_or_code)).first()
        else:
            plant = db.query(Plant).filter(Plant.code == str(plant_id_or_code).upper()).first()

        if not plant:
            raise ValueError(f"Plant '{plant_id_or_code}' not found.")

        # Generate plant forecast
        fc = self.forecast_service.generate_plant_forecast(
            db=db,
            plant_id=plant.id,
            horizon_hours=horizon_hours,
            save_to_db=True
        )

        region = db.query(Region).filter(Region.id == plant.region_id).first()
        state = db.query(State).filter(State.id == plant.state_id).first()

        return {
            "level": "farm",
            "plant_id": plant.id,
            "plant_code": plant.code,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "capacity_mw": float(plant.capacity_mw),
            "region_id": plant.region_id,
            "region_code": region.code if region else "N/A",
            "region_name": region.name if region else "N/A",
            "state_id": plant.state_id,
            "state_code": state.code if state else "N/A",
            "state_name": state.name if state else "N/A",
            "latitude": float(plant.latitude),
            "longitude": float(plant.longitude),
            "elevation_m": float(plant.elevation_m) if plant.elevation_m else None,
            "technology": plant.technology,
            "commissioning_year": plant.commissioning_year,
            "operator_name": plant.operator_name,
            "horizon_hours": horizon_hours,
            "peak_generation_mw": fc["peak_generation_mw"],
            "peak_generation_timestamp": fc["peak_generation_timestamp"],
            "average_generation_mw": fc["average_generation_mw"],
            "expected_total_mwh": fc["expected_total_mwh"],
            "solar_total_mwh": fc["solar_total_mwh"],
            "wind_total_mwh": fc["wind_total_mwh"],
            "capacity_factor_pct": fc["capacity_factor_pct"],
            "average_confidence": fc["average_confidence"],
            "ramp_events_count": fc["ramp_events_count"],
            "ramp_events": fc["ramp_events"],
            "forecast_points": fc["forecast_points"]
        }

    # -------------------------------------------------------------------------
    # 2. REGION LEVEL AGGREGATION
    # -------------------------------------------------------------------------
    def aggregate_region(
        self,
        db: Session,
        region_id_or_code: Union[int, str],
        horizon_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Bottom-up hierarchical aggregation across all renewable facilities in a regional grid.
        """
        if isinstance(region_id_or_code, int) or (isinstance(region_id_or_code, str) and region_id_or_code.isdigit()):
            region = db.query(Region).filter(Region.id == int(region_id_or_code)).first()
        else:
            region = db.query(Region).filter(Region.code == str(region_id_or_code).upper()).first()

        if not region:
            raise ValueError(f"Region '{region_id_or_code}' not found.")

        plants = db.query(Plant).filter(
            Plant.region_id == region.id,
            Plant.status == "active"
        ).all()

        if not plants:
            return self._empty_aggregated_response(
                level="region",
                entity_id=region.id,
                entity_code=region.code,
                entity_name=region.name,
                horizon_hours=horizon_hours
            )

        # Collect farm-level forecasts
        farm_forecasts = [self.aggregate_farm(db, p.id, horizon_hours) for p in plants]

        # Conserve and sum time series
        aggregated_data = self._aggregate_forecast_points(farm_forecasts, horizon_hours)

        # Region capacity breakdown
        total_cap = sum(p["capacity_mw"] for p in farm_forecasts)
        solar_cap = sum(
            p["capacity_mw"] if p["plant_type"] == "solar"
            else (p["capacity_mw"] * 0.6 if p["plant_type"] == "hybrid" else 0.0)
            for p in farm_forecasts
        )
        wind_cap = sum(
            p["capacity_mw"] if p["plant_type"] == "wind"
            else (p["capacity_mw"] * 0.4 if p["plant_type"] == "hybrid" else 0.0)
            for p in farm_forecasts
        )

        plants_breakdown = [
            {
                "plant_id": f["plant_id"],
                "plant_code": f["plant_code"],
                "plant_name": f["plant_name"],
                "plant_type": f["plant_type"],
                "state_code": f["state_code"],
                "capacity_mw": f["capacity_mw"],
                "peak_mw": f["peak_generation_mw"],
                "expected_total_mwh": f["expected_total_mwh"],
                "capacity_factor_pct": f["capacity_factor_pct"],
                "average_confidence": f["average_confidence"]
            }
            for f in farm_forecasts
        ]

        total_mwh = aggregated_data["expected_total_mwh"]
        solar_mwh = aggregated_data["solar_total_mwh"]
        wind_mwh = aggregated_data["wind_total_mwh"]
        cf_pct = round(aggregated_data["average_generation_mw"] / total_cap * 100, 2) if total_cap > 0 else 0.0

        return {
            "level": "region",
            "entity_id": region.id,
            "entity_code": region.code,
            "entity_name": region.name,
            "horizon_hours": horizon_hours,
            "total_capacity_mw": round(total_cap, 2),
            "installed_solar_mw": round(solar_cap, 2),
            "installed_wind_mw": round(wind_cap, 2),
            "plants_count": len(plants),
            "peak_generation_mw": aggregated_data["peak_generation_mw"],
            "peak_generation_timestamp": aggregated_data["peak_generation_timestamp"],
            "average_generation_mw": aggregated_data["average_generation_mw"],
            "expected_total_mwh": total_mwh,
            "solar_total_mwh": solar_mwh,
            "wind_total_mwh": wind_mwh,
            "solar_contribution_pct": round(solar_mwh / total_mwh * 100, 2) if total_mwh > 0 else 0.0,
            "wind_contribution_pct": round(wind_mwh / total_mwh * 100, 2) if total_mwh > 0 else 0.0,
            "capacity_factor_pct": cf_pct,
            "average_confidence": aggregated_data["average_confidence"],
            "plants_breakdown": plants_breakdown,
            "forecast_points": aggregated_data["forecast_points"]
        }

    # -------------------------------------------------------------------------
    # 3. STATE LEVEL AGGREGATION
    # -------------------------------------------------------------------------
    def aggregate_state(
        self,
        db: Session,
        state_id_or_code: Union[int, str],
        horizon_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Bottom-up hierarchical aggregation across all renewable facilities in a state.
        """
        if isinstance(state_id_or_code, int) or (isinstance(state_id_or_code, str) and state_id_or_code.isdigit()):
            state = db.query(State).filter(State.id == int(state_id_or_code)).first()
        else:
            state = db.query(State).filter(State.code == str(state_id_or_code).upper()).first()

        if not state:
            raise ValueError(f"State '{state_id_or_code}' not found.")

        region = db.query(Region).filter(Region.id == state.region_id).first()

        plants = db.query(Plant).filter(
            Plant.state_id == state.id,
            Plant.status == "active"
        ).all()

        if not plants:
            return self._empty_aggregated_response(
                level="state",
                entity_id=state.id,
                entity_code=state.code,
                entity_name=state.name,
                horizon_hours=horizon_hours,
                region_code=region.code if region else None
            )

        # Collect farm-level forecasts
        farm_forecasts = [self.aggregate_farm(db, p.id, horizon_hours) for p in plants]

        # Conserve and sum time series
        aggregated_data = self._aggregate_forecast_points(farm_forecasts, horizon_hours)

        total_cap = sum(p["capacity_mw"] for p in farm_forecasts)
        solar_cap = sum(
            p["capacity_mw"] if p["plant_type"] == "solar"
            else (p["capacity_mw"] * 0.6 if p["plant_type"] == "hybrid" else 0.0)
            for p in farm_forecasts
        )
        wind_cap = sum(
            p["capacity_mw"] if p["plant_type"] == "wind"
            else (p["capacity_mw"] * 0.4 if p["plant_type"] == "hybrid" else 0.0)
            for p in farm_forecasts
        )

        plants_breakdown = [
            {
                "plant_id": f["plant_id"],
                "plant_code": f["plant_code"],
                "plant_name": f["plant_name"],
                "plant_type": f["plant_type"],
                "capacity_mw": f["capacity_mw"],
                "peak_mw": f["peak_generation_mw"],
                "expected_total_mwh": f["expected_total_mwh"],
                "capacity_factor_pct": f["capacity_factor_pct"],
                "average_confidence": f["average_confidence"]
            }
            for f in farm_forecasts
        ]

        total_mwh = aggregated_data["expected_total_mwh"]
        solar_mwh = aggregated_data["solar_total_mwh"]
        wind_mwh = aggregated_data["wind_total_mwh"]
        cf_pct = round(aggregated_data["average_generation_mw"] / total_cap * 100, 2) if total_cap > 0 else 0.0

        return {
            "level": "state",
            "entity_id": state.id,
            "entity_code": state.code,
            "entity_name": state.name,
            "region_code": region.code if region else "N/A",
            "region_name": region.name if region else "N/A",
            "horizon_hours": horizon_hours,
            "total_capacity_mw": round(total_cap, 2),
            "installed_solar_mw": round(solar_cap, 2),
            "installed_wind_mw": round(wind_cap, 2),
            "plants_count": len(plants),
            "peak_generation_mw": aggregated_data["peak_generation_mw"],
            "peak_generation_timestamp": aggregated_data["peak_generation_timestamp"],
            "average_generation_mw": aggregated_data["average_generation_mw"],
            "expected_total_mwh": total_mwh,
            "solar_total_mwh": solar_mwh,
            "wind_total_mwh": wind_mwh,
            "solar_contribution_pct": round(solar_mwh / total_mwh * 100, 2) if total_mwh > 0 else 0.0,
            "wind_contribution_pct": round(wind_mwh / total_mwh * 100, 2) if total_mwh > 0 else 0.0,
            "capacity_factor_pct": cf_pct,
            "average_confidence": aggregated_data["average_confidence"],
            "plants_breakdown": plants_breakdown,
            "forecast_points": aggregated_data["forecast_points"]
        }

    # -------------------------------------------------------------------------
    # 4. NATIONAL LEVEL AGGREGATION
    # -------------------------------------------------------------------------
    def aggregate_national(
        self,
        db: Session,
        horizon_hours: int = 24
    ) -> Dict[str, Any]:
        """
        All-India National Grid renewable generation forecast aggregation.
        Rolls up all registered renewable facilities across all regions and states.
        Strictly conserves energy: National(t) = Sum(Region_i(t)).
        """
        plants = db.query(Plant).filter(Plant.status == "active").all()
        if not plants:
            return self._empty_aggregated_response(
                level="national",
                entity_id=0,
                entity_code="IND",
                entity_name="All-India National Grid",
                horizon_hours=horizon_hours
            )

        # Collect farm forecasts for all facilities
        farm_forecasts = [self.aggregate_farm(db, p.id, horizon_hours) for p in plants]

        # Conserve and sum time series
        aggregated_data = self._aggregate_forecast_points(farm_forecasts, horizon_hours)

        total_cap = sum(p["capacity_mw"] for p in farm_forecasts)
        solar_cap = sum(
            p["capacity_mw"] if p["plant_type"] == "solar"
            else (p["capacity_mw"] * 0.6 if p["plant_type"] == "hybrid" else 0.0)
            for p in farm_forecasts
        )
        wind_cap = sum(
            p["capacity_mw"] if p["plant_type"] == "wind"
            else (p["capacity_mw"] * 0.4 if p["plant_type"] == "hybrid" else 0.0)
            for p in farm_forecasts
        )

        total_mwh = aggregated_data["expected_total_mwh"]
        solar_mwh = aggregated_data["solar_total_mwh"]
        wind_mwh = aggregated_data["wind_total_mwh"]
        cf_pct = round(aggregated_data["average_generation_mw"] / total_cap * 100, 2) if total_cap > 0 else 0.0

        # Regional Breakdown
        regional_dict: Dict[str, Dict[str, Any]] = {}
        for f in farm_forecasts:
            rc = f["region_code"]
            if rc not in regional_dict:
                regional_dict[rc] = {
                    "region_code": rc,
                    "region_name": f["region_name"],
                    "capacity_mw": 0.0,
                    "total_mwh": 0.0,
                    "peak_mw": 0.0,
                    "plants_count": 0
                }
            regional_dict[rc]["capacity_mw"] += f["capacity_mw"]
            regional_dict[rc]["total_mwh"] += f["expected_total_mwh"]
            regional_dict[rc]["plants_count"] += 1

        regional_summaries = []
        for rc, rdata in regional_dict.items():
            rdata["capacity_mw"] = round(rdata["capacity_mw"], 2)
            rdata["total_mwh"] = round(rdata["total_mwh"], 2)
            rdata["generation_share_pct"] = round(rdata["total_mwh"] / total_mwh * 100, 2) if total_mwh > 0 else 0.0
            regional_summaries.append(rdata)

        # State Breakdown
        state_dict: Dict[str, Dict[str, Any]] = {}
        for f in farm_forecasts:
            sc = f["state_code"]
            if sc not in state_dict:
                state_dict[sc] = {
                    "state_code": sc,
                    "state_name": f["state_name"],
                    "region_code": f["region_code"],
                    "capacity_mw": 0.0,
                    "total_mwh": 0.0,
                    "plants_count": 0
                }
            state_dict[sc]["capacity_mw"] += f["capacity_mw"]
            state_dict[sc]["total_mwh"] += f["expected_total_mwh"]
            state_dict[sc]["plants_count"] += 1

        state_summaries = []
        for sc, sdata in state_dict.items():
            sdata["capacity_mw"] = round(sdata["capacity_mw"], 2)
            sdata["total_mwh"] = round(sdata["total_mwh"], 2)
            sdata["generation_share_pct"] = round(sdata["total_mwh"] / total_mwh * 100, 2) if total_mwh > 0 else 0.0
            state_summaries.append(sdata)

        # Transmission balancing volatility / ramp risk index
        points = aggregated_data["forecast_points"]
        max_ramp = 0.0
        for i in range(1, len(points)):
            ramp = abs(points[i]["predicted_mw"] - points[i - 1]["predicted_mw"])
            if ramp > max_ramp:
                max_ramp = ramp

        ramp_fraction = (max_ramp / total_cap) if total_cap > 0 else 0.0
        if ramp_fraction >= 0.20:
            balancing_risk = "HIGH"
        elif ramp_fraction >= 0.10:
            balancing_risk = "MODERATE"
        else:
            balancing_risk = "LOW"

        return {
            "level": "national",
            "country": "India",
            "grid_operator": "NLDC / POSOCO / Grid-India",
            "horizon_hours": horizon_hours,
            "total_capacity_mw": round(total_cap, 2),
            "installed_solar_mw": round(solar_cap, 2),
            "installed_wind_mw": round(wind_cap, 2),
            "active_plants_count": len(plants),
            "national_peak_mw": aggregated_data["peak_generation_mw"],
            "national_peak_timestamp": aggregated_data["peak_generation_timestamp"],
            "average_generation_mw": aggregated_data["average_generation_mw"],
            "expected_total_mwh": total_mwh,
            "expected_daily_generation_mwh": round(total_mwh * (24.0 / horizon_hours), 2),
            "solar_total_mwh": solar_mwh,
            "wind_total_mwh": wind_mwh,
            "solar_contribution_pct": round(solar_mwh / total_mwh * 100, 2) if total_mwh > 0 else 0.0,
            "wind_contribution_pct": round(wind_mwh / total_mwh * 100, 2) if total_mwh > 0 else 0.0,
            "capacity_factor_pct": cf_pct,
            "average_confidence": aggregated_data["average_confidence"],
            "grid_balancing_risk": balancing_risk,
            "max_hourly_ramp_mw": round(max_ramp, 2),
            "regional_summaries": regional_summaries,
            "state_summaries": state_summaries,
            "forecast_points": aggregated_data["forecast_points"]
        }

    # -------------------------------------------------------------------------
    # 5. HIERARCHICAL DRILLDOWN NAVIGATION TREE
    # -------------------------------------------------------------------------
    def get_hierarchical_tree(self, db: Session) -> Dict[str, Any]:
        """
        Returns full navigation drill-down tree:
        National -> Regions -> States -> Renewable Facilities
        """
        regions = db.query(Region).order_by(Region.name.asc()).all()
        total_national_cap = 0.0

        regions_list = []
        for r in regions:
            r_cap = 0.0
            states_list = []
            states = db.query(State).filter(State.region_id == r.id).order_by(State.name.asc()).all()

            for s in states:
                s_cap = 0.0
                plants = db.query(Plant).filter(Plant.state_id == s.id, Plant.status == "active").all()
                plants_list = []
                for p in plants:
                    p_cap = float(p.capacity_mw)
                    s_cap += p_cap
                    plants_list.append({
                        "id": p.id,
                        "code": p.code,
                        "name": p.name,
                        "plant_type": p.plant_type,
                        "capacity_mw": p_cap,
                        "latitude": float(p.latitude),
                        "longitude": float(p.longitude),
                        "technology": p.technology,
                        "status": p.status
                    })

                r_cap += s_cap
                states_list.append({
                    "id": s.id,
                    "code": s.code,
                    "name": s.name,
                    "total_capacity_mw": round(s_cap, 2),
                    "plants_count": len(plants_list),
                    "plants": plants_list
                })

            total_national_cap += r_cap
            regions_list.append({
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "total_capacity_mw": round(r_cap, 2),
                "states_count": len(states_list),
                "states": states_list
            })

        return {
            "level": "national",
            "country": "India",
            "code": "IND",
            "name": "All-India Interconnected Grid",
            "total_capacity_mw": round(total_national_cap, 2),
            "regions_count": len(regions_list),
            "regions": regions_list
        }

    # -------------------------------------------------------------------------
    # INTERNAL HELPER: Time-series alignment & mathematical conservation
    # -------------------------------------------------------------------------
    def _aggregate_forecast_points(
        self,
        forecast_list: List[Dict[str, Any]],
        horizon_hours: int
    ) -> Dict[str, Any]:
        """
        Merge hourly forecast points across all entities with strict conservation.
        """
        if not forecast_list:
            return {
                "peak_generation_mw": 0.0,
                "peak_generation_timestamp": None,
                "average_generation_mw": 0.0,
                "expected_total_mwh": 0.0,
                "solar_total_mwh": 0.0,
                "wind_total_mwh": 0.0,
                "average_confidence": 0.90,
                "forecast_points": []
            }

        # Number of points is horizon_hours
        point_count = min(len(f["forecast_points"]) for f in forecast_list)
        aggregated_points = []
        total_weights = sum(f["capacity_mw"] for f in forecast_list)

        for i in range(point_count):
            ts = forecast_list[0]["forecast_points"][i]["timestamp"]
            pred_mw = sum(f["forecast_points"][i]["predicted_mw"] for f in forecast_list)
            solar_mw = sum(f["forecast_points"][i].get("solar_mw", 0.0) for f in forecast_list)
            wind_mw = sum(f["forecast_points"][i].get("wind_mw", 0.0) for f in forecast_list)
            lower_mw = sum(f["forecast_points"][i]["lower_bound_mw"] for f in forecast_list)
            upper_mw = sum(f["forecast_points"][i]["upper_bound_mw"] for f in forecast_list)

            if total_weights > 0:
                weighted_conf = sum(
                    f["forecast_points"][i]["confidence_score"] * f["capacity_mw"]
                    for f in forecast_list
                ) / total_weights
            else:
                weighted_conf = 0.90

            aggregated_points.append({
                "timestamp": ts,
                "horizon_hours": horizon_hours,
                "predicted_mw": round(pred_mw, 2),
                "solar_mw": round(solar_mw, 2),
                "wind_mw": round(wind_mw, 2),
                "lower_bound_mw": round(lower_mw, 2),
                "upper_bound_mw": round(upper_mw, 2),
                "confidence_score": round(float(weighted_conf), 2)
            })

        mw_vals = [p["predicted_mw"] for p in aggregated_points]
        peak_mw = max(mw_vals) if mw_vals else 0.0
        peak_idx = mw_vals.index(peak_mw) if mw_vals else 0
        peak_time = aggregated_points[peak_idx]["timestamp"] if aggregated_points else None

        avg_mw = sum(mw_vals) / len(mw_vals) if mw_vals else 0.0
        tot_mwh = sum(mw_vals)
        sol_mwh = sum(p["solar_mw"] for p in aggregated_points)
        wnd_mwh = sum(p["wind_mw"] for p in aggregated_points)
        avg_conf = float(np.mean([p["confidence_score"] for p in aggregated_points])) if aggregated_points else 0.90

        return {
            "peak_generation_mw": round(peak_mw, 2),
            "peak_generation_timestamp": peak_time,
            "average_generation_mw": round(avg_mw, 2),
            "expected_total_mwh": round(tot_mwh, 2),
            "solar_total_mwh": round(sol_mwh, 2),
            "wind_total_mwh": round(wnd_mwh, 2),
            "average_confidence": round(avg_conf, 2),
            "forecast_points": aggregated_points
        }

    def _empty_aggregated_response(
        self,
        level: str,
        entity_id: int,
        entity_code: str,
        entity_name: str,
        horizon_hours: int,
        region_code: Optional[str] = None
    ) -> Dict[str, Any]:
        resp = {
            "level": level,
            "entity_id": entity_id,
            "entity_code": entity_code,
            "entity_name": entity_name,
            "horizon_hours": horizon_hours,
            "total_capacity_mw": 0.0,
            "installed_solar_mw": 0.0,
            "installed_wind_mw": 0.0,
            "plants_count": 0,
            "peak_generation_mw": 0.0,
            "peak_generation_timestamp": None,
            "average_generation_mw": 0.0,
            "expected_total_mwh": 0.0,
            "solar_total_mwh": 0.0,
            "wind_total_mwh": 0.0,
            "solar_contribution_pct": 0.0,
            "wind_contribution_pct": 0.0,
            "capacity_factor_pct": 0.0,
            "average_confidence": 0.90,
            "plants_breakdown": [],
            "forecast_points": []
        }
        if region_code:
            resp["region_code"] = region_code
        return resp

# Singleton instance
aggregation_engine = AggregationEngine()
