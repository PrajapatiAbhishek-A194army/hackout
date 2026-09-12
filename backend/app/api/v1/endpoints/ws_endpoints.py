import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, Path
from sqlalchemy.orm import Session

from app.database.session import get_db, SessionLocal
from app.models.plant import Plant
from app.websockets.manager import connection_manager
from app.websockets.streamer import telemetry_streamer
from app.schemas.telemetry import TelemetryStatsResponse

logger = logging.getLogger("backend.api.websockets")

router = APIRouter()

# -------------------------------------------------------------------------
# WebSocket Streaming Endpoints
# -------------------------------------------------------------------------

@router.websocket("/ws/live")
async def websocket_multiplexed_live(websocket: WebSocket):
    """
    Universal multiplexed real-time streaming channel.
    Default subscriptions: 'global_grid', 'alerts'.
    Supports client subscription messages:
      {"action": "subscribe", "topic": "plant:1"}
      {"action": "unsubscribe", "topic": "plant:1"}
      {"action": "ping"}
    """
    await connection_manager.connect(websocket, default_topics=["global_grid", "alerts"])

    # Push initial connection snapshot
    db = SessionLocal()
    try:
        initial_grid = telemetry_streamer.generate_grid_telemetry(db)
        await connection_manager.send_personal_message(
            {
                "type": "connection_established",
                "topic": "system",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "message": "Connected to GridFlow Real-Time Streaming Gateway",
                    "initial_grid": initial_grid.model_dump(mode="json"),
                    "subscribed_topics": list(connection_manager.client_subscriptions.get(websocket, []))
                }
            },
            websocket
        )
    finally:
        db.close()

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
                action = msg.get("action", "").lower()
                topic = msg.get("topic")

                if action == "subscribe" and topic:
                    connection_manager.subscribe(websocket, topic)
                    await connection_manager.send_personal_message(
                        {"type": "subscription_ack", "topic": topic, "status": "subscribed"},
                        websocket
                    )
                elif action == "unsubscribe" and topic:
                    connection_manager.unsubscribe(websocket, topic)
                    await connection_manager.send_personal_message(
                        {"type": "unsubscription_ack", "topic": topic, "status": "unsubscribed"},
                        websocket
                    )
                elif action == "ping":
                    await connection_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                        websocket
                    )
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket client loop terminated: {e}")
        connection_manager.disconnect(websocket)

@router.websocket("/ws/plants/{plant_id}")
async def websocket_direct_plant(
    websocket: WebSocket,
    plant_id: int = Path(..., description="Target plant ID")
):
    """
    Dedicated high-frequency telemetry stream for a specific renewable facility.
    """
    topic = f"plant:{plant_id}"
    await connection_manager.connect(websocket, default_topics=[topic])

    # Send initial plant frame
    db = SessionLocal()
    try:
        plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if plant:
            plant_data = telemetry_streamer.generate_plant_telemetry(plant)
            await connection_manager.send_personal_message(
                {
                    "type": "plant_telemetry",
                    "topic": topic,
                    "timestamp": datetime.now().isoformat(),
                    "data": plant_data.model_dump(mode="json")
                },
                websocket
            )
    finally:
        db.close()

    try:
        while True:
            data = await websocket.receive_text()
            if "ping" in data.lower():
                await connection_manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.now().isoformat()},
                    websocket
                )
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception:
        connection_manager.disconnect(websocket)

@router.websocket("/ws/alerts")
async def websocket_direct_alerts(websocket: WebSocket):
    """
    Dedicated broadcast stream for critical grid alerts, trip hazards, and ramp rate alarms.
    """
    await connection_manager.connect(websocket, default_topics=["alerts"])
    try:
        while True:
            data = await websocket.receive_text()
            if "ping" in data.lower():
                await connection_manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.now().isoformat()},
                    websocket
                )
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception:
        connection_manager.disconnect(websocket)

# -------------------------------------------------------------------------
# REST Telemetry Diagnostic & Control Endpoints
# -------------------------------------------------------------------------

@router.get("/telemetry/current", response_model=Dict[str, Any])
def get_current_telemetry(db: Session = Depends(get_db)):
    """
    HTTP REST snapshot of current All-India grid telemetry and active plant statuses.
    """
    grid = telemetry_streamer.generate_grid_telemetry(db)
    plants = db.query(Plant).filter(Plant.status == "active").all()
    plants_data = [telemetry_streamer.generate_plant_telemetry(p).model_dump(mode="json") for p in plants]

    return {
        "timestamp": datetime.now().isoformat(),
        "grid": grid.model_dump(mode="json"),
        "total_active_plants": len(plants_data),
        "plants": plants_data
    }

@router.post("/telemetry/broadcast", response_model=Dict[str, Any])
async def trigger_telemetry_broadcast(db: Session = Depends(get_db)):
    """
    Forces an immediate real-time broadcast tick to all connected WebSocket clients.
    """
    result = await telemetry_streamer.broadcast_tick(db)
    return {
        "status": "success",
        "broadcast_summary": result,
        "active_ws_connections": len(connection_manager.active_connections)
    }

@router.get("/telemetry/stats", response_model=TelemetryStatsResponse)
def get_telemetry_stats():
    """
    Returns active WebSocket connections and channel subscription metrics.
    """
    stats = connection_manager.get_stats()
    return TelemetryStatsResponse(
        total_active_connections=stats["total_active_connections"],
        connections_by_topic=stats["connections_by_topic"],
        server_time=stats["server_time"]
    )
