import asyncio
import json
import logging
from typing import Dict, Set, List, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("backend.websockets.manager")

class ConnectionManager:
    """
    Asynchronous Multi-Channel WebSocket Pub/Sub Connection Manager.
    Manages client lifetimes, topic subscriptions, and broadcast fan-outs.
    Supported channels:
      - 'global_grid': Live All-India grid telemetry (frequency, renewable MW, demand)
      - 'alerts': Live grid alarm, trip hazard & ramp rate broadcasts
      - 'plant:{plant_id}': High-frequency plant telemetry & inverter state
      - 'region:{region_id}': Regional grid aggregation telemetry
    """

    def __init__(self):
        # All connected clients
        self.active_connections: Set[WebSocket] = set()
        # Topic -> Set of subscribed WebSockets
        self.topic_subscribers: Dict[str, Set[WebSocket]] = {
            "global_grid": set(),
            "alerts": set()
        }
        # WebSocket -> Set of topics client is subscribed to
        self.client_subscriptions: Dict[WebSocket, Set[str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        default_topics: Optional[List[str]] = None
    ):
        """Accepts WebSocket connection and subscribes to initial topics."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.client_subscriptions[websocket] = set()

        # Subscribe to default topics (default: global_grid & alerts)
        topics = default_topics if default_topics is not None else ["global_grid", "alerts"]
        for topic in topics:
            self.subscribe(websocket, topic)

        logger.info(f"WebSocket client connected. Active: {len(self.active_connections)}. Subscribed to: {topics}")

    def disconnect(self, websocket: WebSocket):
        """Removes client from active set and all subscription channels."""
        self.active_connections.discard(websocket)

        subscribed_topics = self.client_subscriptions.pop(websocket, set())
        for topic in subscribed_topics:
            if topic in self.topic_subscribers:
                self.topic_subscribers[topic].discard(websocket)

        logger.info(f"WebSocket client disconnected. Remaining active: {len(self.active_connections)}")

    def subscribe(self, websocket: WebSocket, topic: str):
        """Subscribes a client to a specific topic channel."""
        if topic not in self.topic_subscribers:
            self.topic_subscribers[topic] = set()

        self.topic_subscribers[topic].add(websocket)
        if websocket in self.client_subscriptions:
            self.client_subscriptions[websocket].add(topic)

    def unsubscribe(self, websocket: WebSocket, topic: str):
        """Unsubscribes a client from a specific topic channel."""
        if topic in self.topic_subscribers:
            self.topic_subscribers[topic].discard(websocket)
        if websocket in self.client_subscriptions:
            self.client_subscriptions[websocket].discard(topic)

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Sends a JSON message directly to a specific connected client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send personal WS message: {e}")
            self.disconnect(websocket)

    async def broadcast_to_topic(self, topic: str, message: Dict[str, Any]):
        """
        Broadcasts a JSON message to all clients subscribed to the specified topic.
        Automatically prunes stale or disconnected clients.
        """
        subscribers = self.topic_subscribers.get(topic, set()).copy()
        if not subscribers:
            return

        # Ensure message has timestamp
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        message["topic"] = topic

        stale_clients = []
        for client in subscribers:
            try:
                await client.send_json(message)
            except Exception as e:
                logger.debug(f"Broadcast failed for a subscriber on {topic}: {e}")
                stale_clients.append(client)

        for client in stale_clients:
            self.disconnect(client)

    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcasts a JSON message to every connected WebSocket client."""
        all_clients = self.active_connections.copy()
        if not all_clients:
            return

        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()

        stale_clients = []
        for client in all_clients:
            try:
                await client.send_json(message)
            except Exception:
                stale_clients.append(client)

        for client in stale_clients:
            self.disconnect(client)

    def get_stats(self) -> Dict[str, Any]:
        """Returns active connection count and topic subscription metrics."""
        topic_counts = {t: len(subs) for t, subs in self.topic_subscribers.items()}
        return {
            "total_active_connections": len(self.active_connections),
            "connections_by_topic": topic_counts,
            "server_time": datetime.now()
        }

connection_manager = ConnectionManager()
