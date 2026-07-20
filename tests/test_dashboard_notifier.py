import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from app.modules.dashboard.notifier import ConnectionManager, DashboardNotifier


@pytest.mark.asyncio
async def test_connect_client():
    manager = ConnectionManager()
    mock_ws = AsyncMock(spec=WebSocket)

    await manager.connect(mock_ws)

    mock_ws.accept.assert_called_once()
    assert mock_ws in manager.active_connections
    assert len(manager.active_connections) == 1


@pytest.mark.asyncio
async def test_disconnect_client():
    manager = ConnectionManager()
    mock_ws = AsyncMock(spec=WebSocket)

    await manager.connect(mock_ws)
    manager.disconnect(mock_ws)

    assert mock_ws not in manager.active_connections
    assert len(manager.active_connections) == 0


@pytest.mark.asyncio
async def test_broadcast_to_single_client():
    manager = ConnectionManager()
    mock_ws = AsyncMock(spec=WebSocket)

    await manager.connect(mock_ws)
    await manager.broadcast("hello")

    mock_ws.send_text.assert_called_once_with("hello")


@pytest.mark.asyncio
async def test_broadcast_to_multiple_clients():
    manager = ConnectionManager()
    clients = [AsyncMock(spec=WebSocket) for _ in range(3)]

    for client in clients:
        await manager.connect(client)

    await manager.broadcast("ping")

    for client in clients:
        client.send_text.assert_called_once_with("ping")


@pytest.mark.asyncio
async def test_broadcast_disconnects_failed_client():
    manager = ConnectionManager()
    good_client = AsyncMock(spec=WebSocket)
    bad_client = AsyncMock(spec=WebSocket)
    bad_client.send_text.side_effect = RuntimeError("broken pipe")

    await manager.connect(good_client)
    await manager.connect(bad_client)
    await manager.broadcast("event")

    # Good client received the message
    good_client.send_text.assert_called_once_with("event")
    # Bad client is disconnected after failure
    assert bad_client not in manager.active_connections


@pytest.mark.asyncio
async def test_notifier_order_created():
    mock_manager = AsyncMock(spec=ConnectionManager)
    notifier = DashboardNotifier(mock_manager)

    await notifier.notify_order_created("ORD-001")

    expected_payload = json.dumps({"type": "ORDER_CREATED", "data": {"order_id": "ORD-001"}})
    mock_manager.broadcast.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_notifier_inventory_updated():
    mock_manager = AsyncMock(spec=ConnectionManager)
    notifier = DashboardNotifier(mock_manager)

    await notifier.notify_inventory_updated(product_id=42, available=100)

    expected_payload = json.dumps({
        "type": "INVENTORY_UPDATED",
        "data": {"product_id": 42, "available": 100}
    })
    mock_manager.broadcast.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_notifier_new_alert():
    mock_manager = AsyncMock(spec=ConnectionManager)
    notifier = DashboardNotifier(mock_manager)

    await notifier.notify_new_alert(alert_id=1, message="Low stock")

    expected_payload = json.dumps({
        "type": "NEW_ALERT",
        "data": {"alert_id": 1, "message": "Low stock"}
    })
    mock_manager.broadcast.assert_called_once_with(expected_payload)
