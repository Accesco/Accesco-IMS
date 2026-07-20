import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("dashboard.notifier")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        # Snapshot the list before iterating so that disconnect() calls
        # (which mutate active_connections via list.remove) cannot cause the
        # iterator to skip subsequent clients.
        failed: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to client: {e}")
                failed.append(connection)
        for connection in failed:
            self.disconnect(connection)

class DashboardNotifier:
    def __init__(self, manager: ConnectionManager):
        self.manager = manager

    async def notify(self, event_type: str, data: Dict[str, Any] = None):
        if data is None:
            data = {}
            
        payload = {
            "type": event_type,
            "data": data
        }
        message = json.dumps(payload)
        logger.info(f"Broadcasting event: {event_type}")
        await self.manager.broadcast(message)

    async def notify_order_created(self, order_id: str):
        await self.notify("ORDER_CREATED", {"order_id": order_id})

    async def notify_order_updated(self, order_id: str, status: str):
        await self.notify("ORDER_UPDATED", {"order_id": order_id, "status": status})

    async def notify_inventory_updated(self, product_id: int, available: int):
        await self.notify("INVENTORY_UPDATED", {"product_id": product_id, "available": available})

    async def notify_new_alert(self, alert_id: int, message: str):
        await self.notify("NEW_ALERT", {"alert_id": alert_id, "message": message})
        
    async def notify_compliance_updated(self, audit_id: int):
        await self.notify("COMPLIANCE_UPDATED", {"audit_id": audit_id})

# Global instance
manager = ConnectionManager()
notifier = DashboardNotifier(manager)

def get_notifier() -> DashboardNotifier:
    return notifier

def get_connection_manager() -> ConnectionManager:
    return manager
