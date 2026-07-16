"""
Real-time event publishing helpers.

Provides a unified function to emit structured events to WebSocket
clients after successful database operations. Events are broadcast
through the ConnectionManager which uses Redis Pub/Sub when available.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.modules.websocket.manager import ws_manager, build_event_envelope

logger = logging.getLogger("websocket_events")


async def publish_event(
    event_type: str,
    entity_type: str,
    entity_id: Any,
    data: dict,
    timestamp: Optional[datetime] = None,
) -> None:
    """
    Publish a real-time event to all connected WebSocket clients.

    This should only be called after the corresponding database
    transaction has been successfully committed.

    Args:
        event_type: Event name (e.g., ORDER_STATUS_CHANGED, RIDER_ASSIGNED)
        entity_type: Entity category (e.g., "order", "rider", "dispatch")
        entity_id: Primary key of the affected entity
        data: Event payload dict (must be JSON-serializable)
        timestamp: Optional override; defaults to current UTC time
    """
    envelope = build_event_envelope(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data,
        timestamp=timestamp,
    )

    try:
        await ws_manager.broadcast(envelope)
        logger.info(f"Published {event_type} for {entity_type}:{entity_id}")
    except Exception as e:
        # Real-time delivery is best-effort; never fail the request
        logger.error(f"Failed to publish WebSocket event {event_type}: {e}")
