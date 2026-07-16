"""
WebSocket Connection Manager with Redis Pub/Sub for cross-instance broadcasting.

Manages authenticated WebSocket connections, event broadcasting,
and cleanup for the Accesco Living IMS real-time event system.
"""

import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger("websocket_manager")


class ConnectionManager:
    """
    Manages active WebSocket connections and broadcasts structured events.

    Supports Redis Pub/Sub for multi-instance deployments. When Redis is
    unavailable, falls back to local-only broadcasting.
    """

    def __init__(self):
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._user_meta: Dict[int, dict] = {}
        self._pubsub_task: Optional[asyncio.Task] = None
        self._redis_pubsub = None
        self._channel = "ims:realtime_events"

    async def start(self, redis_service=None) -> None:
        """Initialize the manager and start Redis Pub/Sub listener if available."""
        if redis_service and redis_service.client:
            try:
                self._redis_pubsub = redis_service.client.pubsub()
                await self._redis_pubsub.subscribe(self._channel)
                self._pubsub_task = asyncio.create_task(self._listen_redis())
                logger.info("WebSocket manager started with Redis Pub/Sub")
            except Exception as e:
                logger.warning(f"Redis Pub/Sub unavailable, using local-only: {e}")
                self._redis_pubsub = None
        else:
            logger.info("WebSocket manager started (local-only, no Redis)")

    async def stop(self) -> None:
        """Shut down the manager, cancel Pub/Sub listener, close connections."""
        if self._pubsub_task and not self._pubsub_task.done():
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        if self._redis_pubsub:
            await self._redis_pubsub.unsubscribe(self._channel)
            await self._redis_pubsub.close()
            self._redis_pubsub = None

        for user_id in list(self._connections.keys()):
            for ws in list(self._connections.get(user_id, set())):
                try:
                    await ws.close()
                except Exception:
                    pass
            self._connections.pop(user_id, None)

        logger.info("WebSocket manager stopped")

    async def connect(self, websocket: WebSocket, user_id: int, roles: list[str]) -> None:
        """Accept and register a new authenticated WebSocket connection."""
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)
        self._user_meta[user_id] = {"roles": roles}
        logger.info(f"WebSocket connected: user_id={user_id}, roles={roles}")

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """Remove a WebSocket connection and clean up empty user entries."""
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
                self._user_meta.pop(user_id, None)
        logger.info(f"WebSocket disconnected: user_id={user_id}")

    @property
    def active_connection_count(self) -> int:
        return sum(len(sockets) for sockets in self._connections.values())

    async def broadcast(self, event: dict) -> None:
        """
        Broadcast an event to all connected clients.

        If Redis is available, publishes to the Pub/Sub channel so all
        application instances receive the event. Otherwise, delivers locally.
        """
        if self._redis_pubsub and self._redis_pubsub.connection:
            try:
                redis_client = self._redis_pubsub.connection_pool
            except Exception:
                pass
            # Publish via Redis so all instances receive the event
            from app.core.redis import redis_service
            if redis_service.client:
                try:
                    await redis_service.client.publish(
                        self._channel,
                        json.dumps(event, default=str)
                    )
                    return
                except Exception as e:
                    logger.warning(f"Redis publish failed, broadcasting locally: {e}")

        # Local-only fallback
        await self._deliver_to_local_clients(event)

    async def send_to_user(self, user_id: int, event: dict) -> None:
        """Send an event to a specific user's connections."""
        sockets = self._connections.get(user_id)
        if not sockets:
            return

        dead: list[WebSocket] = []
        for ws in list(sockets):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(event)
            except Exception:
                dead.append(ws)

        for ws in dead:
            sockets.discard(ws)

        if not sockets:
            self._connections.pop(user_id, None)
            self._user_meta.pop(user_id, None)
    async def _deliver_to_local_clients(self, event: dict) -> None:
        """Deliver an event to all locally connected WebSocket clients."""
        dead_connections: list[tuple[int, WebSocket]] = []

        for user_id, sockets in list(self._connections.items()):
            for ws in list(sockets):
                try:
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.send_json(event)
                except Exception:
                    dead_connections.append((user_id, ws))
        # Clean up broken connections
        for user_id, ws in dead_connections:
            if user_id in self._connections:
                self._connections[user_id].discard(ws)
                if not self._connections[user_id]:
                    del self._connections[user_id]
                    self._user_meta.pop(user_id, None)

    async def _listen_redis(self) -> None:
        """Background task that listens to Redis Pub/Sub and delivers events locally."""
        try:
            while True:
                message = await self._redis_pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        await self._deliver_to_local_clients(event)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Invalid Redis Pub/Sub message: {e}")
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logger.info("Redis Pub/Sub listener cancelled")
        except Exception as e:
            logger.error(f"Redis Pub/Sub listener error: {e}")


def build_event_envelope(
    event_type: str,
    entity_type: str,
    entity_id: Any,
    data: dict,
    timestamp: Optional[datetime] = None
) -> dict:
    """
    Build a structured event envelope for WebSocket delivery.

    Returns a consistent JSON-serializable dict with event metadata.
    """
    return {
        "event": event_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
        "data": data,
    }


# Singleton instance used across the application
ws_manager = ConnectionManager()
