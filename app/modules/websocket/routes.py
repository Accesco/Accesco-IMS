"""
WebSocket route for authenticated real-time event streaming.

Clients connect with a JWT token as a query parameter. The connection
is authenticated on establishment and events are pushed for the
lifetime of the connection.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import decode_access_token
from app.modules.websocket.manager import ws_manager

logger = logging.getLogger("websocket_routes")

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    """
    Authenticated WebSocket endpoint for real-time event delivery.

    Connect with: ws://<host>/ws?token=<JWT_ACCESS_TOKEN>
    """
    # Authenticate via JWT token
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id_str = payload.get("sub")
    if not user_id_str:
        await websocket.close(code=4001, reason="Token missing user identifier")
        return

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        await websocket.close(code=4001, reason="Invalid user identifier in token")
        return

    roles = payload.get("roles", [])

    # Accept connection and register
    await ws_manager.connect(websocket, user_id, roles)

    try:
        # Keep connection alive, handle client messages
        while True:
            data = await websocket.receive_text()
            # Support ping/pong keepalive from clients
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.warning(f"WebSocket error for user {user_id}: {e}")
        await ws_manager.disconnect(websocket, user_id)
