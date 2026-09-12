from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc
from app.models.region_state import Region, State
from app.models.plant import Plant
from app.models.weather import Weather
from app.models.forecast import Forecast
from app.models.alert_recommendation import Alert, Recommendation
from app.schemas.plant import PlantCreate, PlantUpdate
from app.schemas.forecast import ForecastPoint, FarmForecastResponse, AggregatedForecastResponse, NationalForecastResponse
from app.schemas.alert import AlertStatsResponse

# Regions & States
def get_regions(db: Session) -> List[Region]:
    return db.query(Region).options(joinedload(Region.states)).order_by(Region.name).all()

def get_region_by_id(db: Session, region_id: int) -> Optional[Region]:
    return db.query(Region).options(joinedload(Region.states)).filter(Region.id == region_id).first()

def get_states(db: Session, region_id: Optional[int] = None) -> List[State]:
    query = db.query(State)
    if region_id:
        query = query.filter(State.region_id == region_id)
    return query.order_by(State.name).all()

def get_state_by_id(db: Session, state_id: int) -> Optional[State]:
    return db.query(State).filter(State.id == state_id).first()

# Plants
def get_plants(
    db: Session,
    plant_type: Optional[str] = None,
    region_id: Optional[int] = None,
    state_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Plant]:
    query = db.query(Plant)
    if plant_type:
        query = query.filter(Plant.plant_type == plant_type)
    if region_id:
        query = query.filter(Plant.region_id == region_id)
    if state_id:
        query = query.filter(Plant.state_id == state_id)
    if status:
        query = query.filter(Plant.status == status)
    return query.order_by(Plant.capacity_mw.desc()).offset(skip).limit(limit).all()

def get_plant_by_id(db: Session, plant_id: int) -> Optional[Plant]:
    return db.query(Plant).options(
        joinedload(Plant.region),
        joinedload(Plant.state)
    ).filter(Plant.id == plant_id).first()

def get_plant_by_code(db: Session, code: str) -> Optional[Plant]:
    return db.query(Plant).filter(Plant.code == code).first()

def create_plant(db: Session, plant_in: PlantCreate) -> Plant:
    db_plant = Plant(**plant_in.model_dump())
    db.add(db_plant)
    db.commit()
    db.refresh(db_plant)
    return db_plant

# Weather
def get_weather_for_plant(db: Session, plant_id: int, limit: int = 48) -> List[Weather]:
    return db.query(Weather).filter(
        Weather.plant_id == plant_id
    ).order_by(Weather.timestamp.asc()).limit(limit).all()

# Forecasts
def get_farm_forecast(db: Session, plant_id: int, horizon_hours: int = 24) -> Optional[FarmForecastResponse]:
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        return None

    forecasts = db.query(Forecast).filter(
        Forecast.plant_id == plant_id,
        Forecast.horizon_hours <= horizon_hours
    ).order_by(Forecast.forecast_timestamp.asc()).limit(horizon_hours).all()

    points = [
        ForecastPoint(
            timestamp=f.forecast_timestamp,
            predicted_mw=f.predicted_mw,
            confidence_score=f.confidence_score,
            lower_bound_mw=f.lower_bound_mw,
            upper_bound_mw=f.upper_bound_mw,
            actual_mw=f.actual_mw,
            horizon_hours=f.horizon_hours
        )
        for f in forecasts
    ]

    mw_values = [p.predicted_mw for p in points] if points else [0.0]
    peak_mw = max(mw_values)
    avg_mw = sum(mw_values) / len(mw_values) if mw_values else 0.0
    cf_pct = round((avg_mw / plant.capacity_mw * 100), 2) if plant.capacity_mw > 0 else 0.0

    return FarmForecastResponse(
        plant_id=plant.id,
        plant_name=plant.name,
        plant_type=plant.plant_type,
        capacity_mw=plant.capacity_mw,
        horizon_hours=horizon_hours,
        peak_generation_mw=round(peak_mw, 2),
        average_generation_mw=round(avg_mw, 2),
        capacity_factor_pct=cf_pct,
        forecast_points=points
    )

def get_aggregated_forecast(
    db: Session,
    level: str,
    entity_id: int,
    horizon_hours: int = 24
) -> Optional[AggregatedForecastResponse]:
    if level == "region":
        region = db.query(Region).filter(Region.id == entity_id).first()
        if not region:
            return None
        entity_name = region.name
        entity_code = region.code
        plants = db.query(Plant).filter(Plant.region_id == entity_id).all()
    elif level == "state":
        state = db.query(State).filter(State.id == entity_id).first()
        if not state:
            return None
        entity_name = state.name
        entity_code = state.code
        plants = db.query(Plant).filter(Plant.state_id == entity_id).all()
    else:
        return None

    total_capacity = sum(p.capacity_mw for p in plants)
    plant_ids = [p.id for p in plants]

    if not plant_ids:
        return AggregatedForecastResponse(
            level=level,
            entity_id=entity_id,
            entity_name=entity_name,
            entity_code=entity_code,
            total_capacity_mw=total_capacity,
            horizon_hours=horizon_hours,
            solar_peak_mw=0.0,
            wind_peak_mw=0.0,
            total_peak_mw=0.0,
            forecast_points=[]
        )

    # Group hourly sum across the entity's plants
    results = db.query(
        Forecast.forecast_timestamp,
        func.sum(Forecast.predicted_mw).label("sum_pred"),
        func.sum(Forecast.lower_bound_mw).label("sum_lower"),
        func.sum(Forecast.upper_bound_mw).label("sum_upper"),
        func.avg(Forecast.confidence_score).label("avg_conf")
    ).filter(
        Forecast.plant_id.in_(plant_ids),
        Forecast.horizon_hours <= horizon_hours
    ).group_by(
        Forecast.forecast_timestamp
    ).order_by(
        Forecast.forecast_timestamp.asc()
    ).limit(horizon_hours).all()

    points = [
        ForecastPoint(
            timestamp=row.forecast_timestamp,
            predicted_mw=round(float(row.sum_pred or 0.0), 2),
            confidence_score=round(float(row.avg_conf or 0.90), 2),
            lower_bound_mw=round(float(row.sum_lower or 0.0), 2),
            upper_bound_mw=round(float(row.sum_upper or 0.0), 2),
            actual_mw=None,
            horizon_hours=horizon_hours
        )
        for row in results
    ]

    solar_plants = [p.id for p in plants if p.plant_type == "solar"]
    wind_plants = [p.id for p in plants if p.plant_type == "wind"]

    solar_max = 0.0
    if solar_plants:
        s_res = db.query(func.sum(Forecast.predicted_mw)).filter(
            Forecast.plant_id.in_(solar_plants),
            Forecast.horizon_hours <= horizon_hours
        ).group_by(Forecast.forecast_timestamp).order_by(desc(func.sum(Forecast.predicted_mw))).first()
        solar_max = float(s_res[0]) if s_res else 0.0

    wind_max = 0.0
    if wind_plants:
        w_res = db.query(func.sum(Forecast.predicted_mw)).filter(
            Forecast.plant_id.in_(wind_plants),
            Forecast.horizon_hours <= horizon_hours
        ).group_by(Forecast.forecast_timestamp).order_by(desc(func.sum(Forecast.predicted_mw))).first()
        wind_max = float(w_res[0]) if w_res else 0.0

    total_peak = max([p.predicted_mw for p in points]) if points else 0.0

    return AggregatedForecastResponse(
        level=level,
        entity_id=entity_id,
        entity_name=entity_name,
        entity_code=entity_code,
        total_capacity_mw=round(total_capacity, 2),
        horizon_hours=horizon_hours,
        solar_peak_mw=round(solar_max, 2),
        wind_peak_mw=round(wind_max, 2),
        total_peak_mw=round(total_peak, 2),
        forecast_points=points
    )

def get_national_forecast(db: Session, horizon_hours: int = 24) -> NationalForecastResponse:
    plants = db.query(Plant).all()
    total_capacity = sum(p.capacity_mw for p in plants)

    results = db.query(
        Forecast.forecast_timestamp,
        func.sum(Forecast.predicted_mw).label("sum_pred"),
        func.sum(Forecast.lower_bound_mw).label("sum_lower"),
        func.sum(Forecast.upper_bound_mw).label("sum_upper"),
        func.avg(Forecast.confidence_score).label("avg_conf")
    ).filter(
        Forecast.horizon_hours <= horizon_hours
    ).group_by(
        Forecast.forecast_timestamp
    ).order_by(
        Forecast.forecast_timestamp.asc()
    ).limit(horizon_hours).all()

    points = [
        ForecastPoint(
            timestamp=row.forecast_timestamp,
            predicted_mw=round(float(row.sum_pred or 0.0), 2),
            confidence_score=round(float(row.avg_conf or 0.90), 2),
            lower_bound_mw=round(float(row.sum_lower or 0.0), 2),
            upper_bound_mw=round(float(row.sum_upper or 0.0), 2),
            actual_mw=None,
            horizon_hours=horizon_hours
        )
        for row in results
    ]

    peak_mw = max([p.predicted_mw for p in points]) if points else 0.0
    daily_mwh = sum([p.predicted_mw for p in points]) if points else 0.0

    solar_capacity = sum(p.capacity_mw for p in plants if p.plant_type == "solar")
    wind_capacity = sum(p.capacity_mw for p in plants if p.plant_type == "wind")
    solar_share = round((solar_capacity / total_capacity * 100), 1) if total_capacity > 0 else 60.0
    wind_share = round((100.0 - solar_share), 1)

    return NationalForecastResponse(
        horizon_hours=horizon_hours,
        total_capacity_mw=round(total_capacity, 2),
        national_peak_mw=round(peak_mw, 2),
        expected_daily_generation_mwh=round(daily_mwh, 2),
        solar_contribution_pct=solar_share,
        wind_contribution_pct=wind_share,
        forecast_points=points
    )

# Alerts & Recommendations
def get_alerts(
    db: Session,
    plant_id: Optional[int] = None,
    severity: Optional[str] = None,
    status: Optional[str] = "active",
    limit: int = 50
) -> List[Alert]:
    query = db.query(Alert).options(
        joinedload(Alert.recommendations),
        joinedload(Alert.plant)
    )
    if plant_id:
        query = query.filter(Alert.plant_id == plant_id)
    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)
    return query.order_by(desc(Alert.start_time)).limit(limit).all()

def get_alert_by_id(db: Session, alert_id: int) -> Optional[Alert]:
    return db.query(Alert).options(
        joinedload(Alert.recommendations),
        joinedload(Alert.plant)
    ).filter(Alert.id == alert_id).first()

def get_recommendations(db: Session, alert_id: Optional[int] = None, limit: int = 50) -> List[Recommendation]:
    query = db.query(Recommendation).options(joinedload(Recommendation.alert))
    if alert_id:
        query = query.filter(Recommendation.alert_id == alert_id)
    return query.order_by(Recommendation.priority.asc()).limit(limit).all()

def get_alert_statistics(db: Session) -> AlertStatsResponse:
    alerts = db.query(Alert).filter(Alert.status == "active").all()
    total = len(alerts)
    crit = sum(1 for a in alerts if a.severity == "critical")
    warn = sum(1 for a in alerts if a.severity == "warning")
    info = sum(1 for a in alerts if a.severity == "info")

    over_gen = sum(a.delta_mw or 0.0 for a in alerts if a.alert_type == "over_generation")
    under_gen = sum(a.delta_mw or 0.0 for a in alerts if a.alert_type == "under_generation")

    return AlertStatsResponse(
        total_active_alerts=total,
        critical_alerts=crit,
        warning_alerts=warn,
        info_alerts=info,
        over_generation_mw=round(over_gen, 1),
        under_generation_mw=round(under_gen, 1)
    )
