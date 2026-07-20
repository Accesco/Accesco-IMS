import pytest
import json
from unittest.mock import AsyncMock, MagicMock, call
from app.modules.dashboard.consumer import DashboardEventHandler
from app.modules.dashboard.cache import DashboardCacheManager
from app.modules.dashboard.notifier import DashboardNotifier, ConnectionManager


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_cache_manager():
    manager = AsyncMock(spec=DashboardCacheManager)
    return manager


@pytest.fixture
def mock_notifier():
    notifier = AsyncMock(spec=DashboardNotifier)
    return notifier


@pytest.fixture
def handler(mock_cache_manager, mock_notifier):
    return DashboardEventHandler(mock_cache_manager, mock_notifier)


# ── order.created ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_order_created_invalidates_summary_and_charts(handler, mock_cache_manager, mock_notifier):
    await handler.handle("orders.created", {"order_id": "ORD-001", "store_id": 1, "total_amount": 500.0})

    mock_cache_manager.invalidate_summary.assert_called_once()
    mock_cache_manager.invalidate_charts.assert_called_once()
    mock_notifier.notify_order_created.assert_called_once_with("ORD-001")


# ── orders.updated ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_order_updated_invalidates_summary_and_charts(handler, mock_cache_manager, mock_notifier):
    await handler.handle("orders.updated", {"order_id": "ORD-002", "status": "PROCESSING"})

    mock_cache_manager.invalidate_summary.assert_called_once()
    mock_cache_manager.invalidate_charts.assert_called_once()
    mock_notifier.notify_order_updated.assert_called_once_with("ORD-002", "PROCESSING")


# ── payments.confirmed ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_payment_confirmed_invalidates_summary_and_charts(handler, mock_cache_manager, mock_notifier):
    await handler.handle("payments.confirmed", {"order_id": "ORD-003"})

    mock_cache_manager.invalidate_summary.assert_called_once()
    mock_cache_manager.invalidate_charts.assert_called_once()
    # No WebSocket notification defined for payment confirmation
    mock_notifier.notify_order_created.assert_not_called()


# ── inventory.updated ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inventory_updated_invalidates_inventory_and_summary(handler, mock_cache_manager, mock_notifier):
    await handler.handle("inventory.updated", {"product_id": 42, "available_quantity": 100, "store_id": 1})

    mock_cache_manager.invalidate_inventory.assert_called_once()
    mock_cache_manager.invalidate_summary.assert_called_once()
    mock_notifier.notify_inventory_updated.assert_called_once_with(42, 100)


# ── inventory.low ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inventory_low_invalidates_inventory_and_alerts(handler, mock_cache_manager, mock_notifier):
    await handler.handle("inventory.low", {"product_id": 7, "available_quantity": 3})

    mock_cache_manager.invalidate_inventory.assert_called_once()
    mock_notifier.notify_new_alert.assert_called_once()
    call_args = mock_notifier.notify_new_alert.call_args
    assert call_args.kwargs["alert_id"] == 7
    assert "7" in call_args.kwargs["message"]


# ── shipments.delivered ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_shipment_delivered_invalidates_summary_and_notifies(handler, mock_cache_manager, mock_notifier):
    await handler.handle("shipments.delivered", {"order_id": "ORD-005", "store_id": 2})

    mock_cache_manager.invalidate_summary.assert_called_once()
    mock_cache_manager.invalidate_charts.assert_called_once()
    mock_notifier.notify_order_updated.assert_called_once_with("ORD-005", "DELIVERED")


# ── orders.cancelled ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_order_cancelled_invalidates_summary(handler, mock_cache_manager, mock_notifier):
    await handler.handle("orders.cancelled", {"order_id": "ORD-006"})

    mock_cache_manager.invalidate_summary.assert_called_once()
    mock_notifier.notify_order_updated.assert_called_once_with("ORD-006", "CANCELLED")


# ── Error isolation ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handler_does_not_raise_on_bad_payload(handler):
    """Consumer failures must not propagate. Bad payload should be logged and swallowed."""
    # Missing required field 'order_id'
    await handler.handle("orders.created", {})  # should not raise


@pytest.mark.asyncio
async def test_handler_does_not_raise_on_unknown_topic(handler, mock_cache_manager, mock_notifier):
    """Unknown topics should be silently ignored without any cache or notify calls."""
    await handler.handle("some.unknown.topic", {"foo": "bar"})

    mock_cache_manager.invalidate_summary.assert_not_called()
    mock_notifier.notify_order_created.assert_not_called()


# ── Full Kafka → WebSocket integration flow ───────────────────────────────────

@pytest.mark.asyncio
async def test_order_created_broadcasts_to_websocket_clients():
    """
    Integration: verifies that an orders.created event flows through
    DashboardEventHandler → DashboardNotifier → ConnectionManager → WebSocket clients.
    """
    from fastapi import WebSocket

    # Set up real ConnectionManager and real DashboardNotifier
    connection_manager = ConnectionManager()
    notifier = DashboardNotifier(connection_manager)

    ws_client = AsyncMock(spec=WebSocket)
    await connection_manager.connect(ws_client)

    mock_cache = AsyncMock(spec=DashboardCacheManager)
    event_handler = DashboardEventHandler(mock_cache, notifier)

    await event_handler.handle("orders.created", {"order_id": "ORD-WS-01"})

    # Assert the WebSocket client received a broadcast
    ws_client.send_text.assert_called_once()
    sent_message = json.loads(ws_client.send_text.call_args[0][0])
    assert sent_message["type"] == "ORDER_CREATED"
    assert sent_message["data"]["order_id"] == "ORD-WS-01"
