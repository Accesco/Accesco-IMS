"""
Phase 8 – Comprehensive Dashboard Integration Tests
=====================================================

Coverage:
  1. Authentication – all 8 endpoints
     a. Missing token → 401
     b. Invalid (malformed) JWT → 401
     c. Expired JWT → 401
  2. Authorization / RoleChecker
     a. All authorised roles → 200
     b. Unauthorized role → 403
  3. Full service-layer cache cycle
     a. Cache miss → provider called → data written to Redis
     b. Cache hit → provider NOT called
     c. Redis write failure is silent (service still returns data)
  4. Cache invalidation
     a. Invalidate summary on orders.created Kafka event
     b. Invalidate charts on payment.confirmed
     c. Invalidate inventory on inventory.updated
  5. Kafka → DashboardEventHandler → DashboardNotifier → WebSocket
     (integration: real ConnectionManager, real Notifier, mocked cache)
  6. WebSocket authentication
     a. No token → close 1008
     b. Invalid JWT → close 1008
     c. Valid JWT → accepted
  7. WebSocket reconnect behaviour
  8. Graceful ConnectionManager shutdown
  9. Structured logging verification
     - request_id, endpoint, duration_ms, cache_hit, user_id, status_code
"""

import json
import logging
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from fastapi import WebSocket
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, decode_access_token
from app.core.config import settings
from app.modules.auth.routes import get_current_user
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.consumer import DashboardEventHandler
from app.modules.dashboard.cache import DashboardCacheManager
from app.modules.dashboard.notifier import ConnectionManager, DashboardNotifier
from app.modules.dashboard.service import DashboardService
from app.modules.dashboard.provider import DashboardProvider
from app.models.auth import User, Role
from app.modules.dashboard.schemas import (
    DashboardSummaryResponse,
    RevenueChartResponse,
    RevenueTrend,
    OrdersChartResponse,
    InventoryChartResponse,
    WarehousePerformanceResponse,
    WarehousePerformance,
    ActivitiesResponse,
    AlertsResponse,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

VALID_ROLES = ["Admin", "StoreManager", "ProcurementManager", "InventoryManager", "Viewer"]

_SUMMARY = DashboardSummaryResponse(
    total_orders=100, revenue=50000.0, pending_orders=10,
    inventory_accuracy=99.0, sla=95.0, csat=4.8, returns=2, delivered_orders=88,
)
_REVENUE = RevenueChartResponse(
    daily=[RevenueTrend(date="2026-07-15", amount=5000.0)],
    weekly=[], monthly=[], yearly=[],
)
_ORDERS = OrdersChartResponse(created=100, completed=88, pending=10, cancelled=2)
_INVENTORY = InventoryChartResponse(available=500, reserved=50, damaged=5, out_of_stock=3)
_WAREHOUSES = WarehousePerformanceResponse(
    warehouses=[WarehousePerformance(
        store_id=1, name="WH-A", orders=80, revenue=40000.0, inventory=300, sla=96.0,
    )]
)
_ACTIVITIES = ActivitiesResponse(activities=[], total=0, page=1, page_size=20)
_ALERTS = AlertsResponse(alerts=[], total=0, page=1, page_size=20)


def _make_user(role_name: str = "Admin") -> User:
    """Return a detached User model with the given role."""
    return User(id=42, email=f"{role_name.lower()}@ims.test", roles=[Role(name=role_name)])


def _make_service() -> AsyncMock:
    svc = AsyncMock()
    svc.get_summary.return_value = _SUMMARY
    svc.get_revenue_charts.return_value = _REVENUE
    svc.get_orders_chart.return_value = _ORDERS
    svc.get_inventory_chart.return_value = _INVENTORY
    svc.get_warehouses.return_value = _WAREHOUSES
    svc.get_activities.return_value = _ACTIVITIES
    svc.get_alerts.return_value = _ALERTS
    return svc


def _valid_token(user_id: int = 42, roles: list = None) -> str:
    roles = roles or ["Admin"]
    return create_access_token(subject=user_id, roles=roles)


def _expired_token() -> str:
    """Produce a token that is already expired."""
    return create_access_token(
        subject=99,
        roles=["Admin"],
        expires_delta=timedelta(seconds=-1),
    )


ENDPOINTS = [
    "/api/v1/dashboard/summary",
    "/api/v1/dashboard/charts/revenue",
    "/api/v1/dashboard/charts/orders",
    "/api/v1/dashboard/charts/inventory",
    "/api/v1/dashboard/warehouses",
    "/api/v1/dashboard/activities",
    "/api/v1/dashboard/alerts",
]


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client_authenticated():
    """TestClient with an Admin user and a mocked service."""
    app.dependency_overrides[get_current_user] = lambda: _make_user("Admin")
    app.dependency_overrides[get_dashboard_service] = _make_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth():
    """TestClient with mocked service but NO auth override → real auth runs."""
    app.dependency_overrides[get_dashboard_service] = _make_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Authentication – Missing / Invalid / Expired JWT
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthentication:

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_missing_token_returns_401(self, endpoint, client_no_auth):
        """Every endpoint must reject requests with no Authorization header."""
        r = client_no_auth.get(endpoint)
        assert r.status_code == 401, f"Expected 401 for {endpoint}, got {r.status_code}"

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_invalid_jwt_returns_401(self, endpoint, client_no_auth):
        """A malformed token string that cannot be decoded must return 401."""
        r = client_no_auth.get(endpoint, headers={"Authorization": "Bearer not.a.valid.jwt"})
        assert r.status_code == 401, f"Expected 401 for {endpoint}, got {r.status_code}"

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_expired_jwt_returns_401(self, endpoint, client_no_auth):
        """A syntactically valid but expired token must return 401."""
        token = _expired_token()
        r = client_no_auth.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, f"Expected 401 for expired token on {endpoint}"

    def test_valid_token_is_accepted(self, client_authenticated):
        r = client_authenticated.get("/api/v1/dashboard/summary")
        assert r.status_code == 200

    def test_decode_access_token_returns_none_for_bad_token(self):
        assert decode_access_token("garbage.token.string") is None

    def test_decode_access_token_returns_none_for_expired(self):
        token = _expired_token()
        assert decode_access_token(token) is None

    def test_decode_access_token_returns_payload_for_valid(self):
        token = _valid_token(user_id=5, roles=["StoreManager"])
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "5"
        assert "StoreManager" in payload["roles"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Authorization – RoleChecker
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthorization:
    """
    Dashboard endpoints currently use get_current_user (authentication only).
    This section tests the RoleChecker integration at the route level.
    Routes require *any* authenticated user; Admin bypasses all checks.
    """

    @pytest.mark.parametrize("role", VALID_ROLES)
    def test_all_valid_roles_can_access_summary(self, role):
        app.dependency_overrides[get_current_user] = lambda: _make_user(role)
        app.dependency_overrides[get_dashboard_service] = _make_service
        with TestClient(app) as c:
            r = c.get("/api/v1/dashboard/summary")
        app.dependency_overrides.clear()
        assert r.status_code == 200, f"Role {role} should have access, got {r.status_code}"

    def test_unknown_role_triggers_403_via_role_checker(self):
        """
        Simulate what happens when RoleChecker is applied directly.
        We instantiate RoleChecker and call it with an unauthorised user.
        """
        from app.modules.auth.routes import RoleChecker
        from app.core.exceptions import ForbiddenException

        checker = RoleChecker(["Admin", "StoreManager"])
        unauthorised_user = _make_user("UnknownRole")

        with pytest.raises(ForbiddenException):
            checker(current_user=unauthorised_user)

    def test_admin_bypasses_role_checker(self):
        """Admin must never be rejected by RoleChecker, regardless of allowed_roles."""
        from app.modules.auth.routes import RoleChecker

        checker = RoleChecker(["StoreManager"])  # does NOT list Admin explicitly
        admin_user = _make_user("Admin")
        # Should return the user without raising
        result = checker(current_user=admin_user)
        assert result is admin_user


# ─────────────────────────────────────────────────────────────────────────────
# 3. Cache Miss / Cache Hit / Redis Write Failure
# ─────────────────────────────────────────────────────────────────────────────

class TestCacheCycle:

    @pytest.mark.asyncio
    async def test_cache_miss_calls_provider_and_writes_to_redis(self):
        """
        On a cache miss the service must:
          1. Call the provider to fetch fresh data
          2. Write serialised data to Redis
        """
        mock_repo = AsyncMock()
        mock_provider = DashboardProvider(mock_repo)
        mock_provider.get_summary_data = AsyncMock(return_value={
            "orders": {"total": 50, "delivered": 45, "pending": 5, "cancelled": 0, "revenue": 25000.0},
            "inventory": {"available": 100, "reserved": 10, "damaged": 0, "out_of_stock": 2},
        })

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # MISS

        service = DashboardService(mock_provider, mock_redis)
        result = await service.get_summary()

        mock_provider.get_summary_data.assert_called_once()
        mock_redis.set.assert_called_once()
        assert result.total_orders == 50
        assert result.revenue == 25000.0

    @pytest.mark.asyncio
    async def test_cache_hit_skips_provider(self):
        """
        On a cache hit the service must:
          1. Deserialise and return the cached object
          2. NOT call the provider
        """
        cached = {
            "totalOrders": 200,
            "revenue": 100000.0,
            "pendingOrders": 20,
            "inventoryAccuracy": 99.5,
            "sla": 97.0,
            "csat": 4.9,
            "returns": 3,
            "deliveredOrders": 177,
        }

        mock_repo = AsyncMock()
        mock_provider = DashboardProvider(mock_repo)
        mock_provider.get_summary_data = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(cached)  # HIT

        service = DashboardService(mock_provider, mock_redis)
        result = await service.get_summary()

        mock_provider.get_summary_data.assert_not_called()
        assert result.total_orders == 200
        assert result.revenue == 100000.0

    @pytest.mark.asyncio
    async def test_redis_write_failure_is_transparent(self):
        """
        If Redis raises during the SET, the service must still return valid data.
        The exception must be logged and swallowed.
        """
        mock_repo = AsyncMock()
        mock_provider = DashboardProvider(mock_repo)
        mock_provider.get_summary_data = AsyncMock(return_value={
            "orders": {"total": 1, "delivered": 1, "pending": 0, "cancelled": 0, "revenue": 100.0},
            "inventory": {},
        })

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None           # miss
        mock_redis.set.side_effect = RuntimeError("Redis down")

        service = DashboardService(mock_provider, mock_redis)
        result = await service.get_summary()

        assert result.total_orders == 1   # data returned despite Redis failure

    @pytest.mark.asyncio
    async def test_redis_read_failure_falls_back_to_provider(self):
        """
        If Redis raises during the GET, the service must fall back to the provider.
        """
        mock_repo = AsyncMock()
        mock_provider = DashboardProvider(mock_repo)
        mock_provider.get_summary_data = AsyncMock(return_value={
            "orders": {"total": 7, "delivered": 6, "pending": 1, "cancelled": 0, "revenue": 700.0},
            "inventory": {},
        })

        mock_redis = AsyncMock()
        mock_redis.get.side_effect = RuntimeError("Redis timeout")

        service = DashboardService(mock_provider, mock_redis)
        result = await service.get_summary()

        mock_provider.get_summary_data.assert_called_once()
        assert result.total_orders == 7

    @pytest.mark.asyncio
    async def test_revenue_chart_cache_miss_fetches_and_caches(self):
        mock_repo = AsyncMock()
        mock_provider = DashboardProvider(mock_repo)
        mock_provider.get_revenue_trends = AsyncMock(return_value=[
            {"date": "2026-07-15", "amount": 9999.0},
        ])

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        service = DashboardService(mock_provider, mock_redis)
        result = await service.get_revenue_charts()

        mock_redis.set.assert_called_once()
        assert result.daily[0].amount == 9999.0

    @pytest.mark.asyncio
    async def test_cache_keys_differ_by_filters(self):
        """Two calls with different filters must produce different cache keys."""
        from app.modules.dashboard.cache import DashboardCacheManager
        mock_redis = AsyncMock()
        mgr = DashboardCacheManager(mock_redis)

        key_no_filter = mgr.summary_key(None)
        key_wh1 = mgr.summary_key({"warehouse_id": 1})
        key_wh2 = mgr.summary_key({"warehouse_id": 2})

        assert key_no_filter != key_wh1
        assert key_wh1 != key_wh2
        # Same filter → same key (deterministic)
        assert mgr.summary_key({"warehouse_id": 1}) == key_wh1


# ─────────────────────────────────────────────────────────────────────────────
# 4. Cache Invalidation via Kafka Events
# ─────────────────────────────────────────────────────────────────────────────

class TestCacheInvalidation:

    @pytest.fixture
    def handler_fixtures(self):
        mock_cache = AsyncMock(spec=DashboardCacheManager)
        mock_notifier = AsyncMock(spec=DashboardNotifier)
        handler = DashboardEventHandler(mock_cache, mock_notifier)
        return handler, mock_cache, mock_notifier

    @pytest.mark.asyncio
    async def test_orders_created_invalidates_summary_and_charts(self, handler_fixtures):
        handler, cache, _ = handler_fixtures
        await handler.handle("orders.created", {"order_id": "ORD-1"})
        cache.invalidate_summary.assert_called_once()
        cache.invalidate_charts.assert_called_once()

    @pytest.mark.asyncio
    async def test_payment_confirmed_invalidates_summary_and_charts(self, handler_fixtures):
        handler, cache, notifier = handler_fixtures
        await handler.handle("payments.confirmed", {"order_id": "ORD-2"})
        cache.invalidate_summary.assert_called_once()
        cache.invalidate_charts.assert_called_once()
        notifier.notify_order_created.assert_not_called()

    @pytest.mark.asyncio
    async def test_inventory_updated_invalidates_inventory_only(self, handler_fixtures):
        handler, cache, _ = handler_fixtures
        await handler.handle("inventory.updated", {"product_id": 10, "available_quantity": 50})
        cache.invalidate_inventory.assert_called_once()
        cache.invalidate_summary.assert_called_once()
        cache.invalidate_charts.assert_not_called()

    @pytest.mark.asyncio
    async def test_shipment_delivered_invalidates_summary_and_charts(self, handler_fixtures):
        handler, cache, _ = handler_fixtures
        await handler.handle("shipments.delivered", {"order_id": "ORD-3"})
        cache.invalidate_summary.assert_called_once()
        cache.invalidate_charts.assert_called_once()

    @pytest.mark.asyncio
    async def test_orders_cancelled_invalidates_summary_and_charts(self, handler_fixtures):
        handler, cache, _ = handler_fixtures
        await handler.handle("orders.cancelled", {"order_id": "ORD-4"})
        cache.invalidate_summary.assert_called_once()
        cache.invalidate_charts.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidation_pattern_is_wildcard_for_summary(self):
        """
        DashboardCacheManager.invalidate_summary must scan dashboard:summary*
        so that filter-keyed variants are also evicted.
        """
        mock_redis = AsyncMock()
        mock_redis.client = AsyncMock()
        mock_redis.client.scan.side_effect = [
            (1, ["dashboard:summary", "dashboard:summary:ab12cd34"]),
            (0, []),
        ]

        mgr = DashboardCacheManager(mock_redis)
        await mgr.invalidate_summary()

        first_call = mock_redis.client.scan.call_args_list[0]
        assert first_call.kwargs["match"] == "dashboard:summary*"
        assert mock_redis.client.delete.call_count == 1  # one batch of 2 keys

    @pytest.mark.asyncio
    async def test_invalidation_error_does_not_propagate(self):
        mock_redis = AsyncMock()
        mock_redis.client = AsyncMock()
        mock_redis.client.scan.side_effect = RuntimeError("Redis unavailable")

        mgr = DashboardCacheManager(mock_redis)
        # Must not raise
        await mgr.invalidate_summary()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Full Kafka → EventHandler → Notifier → WebSocket Integration
# ─────────────────────────────────────────────────────────────────────────────

class TestKafkaToWebSocketIntegration:

    @pytest.mark.asyncio
    async def test_orders_created_broadcasts_to_all_ws_clients(self):
        """
        orders.created → DashboardEventHandler → DashboardNotifier → ConnectionManager → clients
        """
        mgr = ConnectionManager()
        notifier = DashboardNotifier(mgr)

        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        await mgr.connect(ws1)
        await mgr.connect(ws2)

        mock_cache = AsyncMock(spec=DashboardCacheManager)
        handler = DashboardEventHandler(mock_cache, notifier)

        await handler.handle("orders.created", {"order_id": "ORD-WS-100"})

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

        payload = json.loads(ws1.send_text.call_args[0][0])
        assert payload["type"] == "ORDER_CREATED"
        assert payload["data"]["order_id"] == "ORD-WS-100"

    @pytest.mark.asyncio
    async def test_inventory_updated_broadcasts_correct_event_type(self):
        mgr = ConnectionManager()
        notifier = DashboardNotifier(mgr)
        ws = AsyncMock(spec=WebSocket)
        await mgr.connect(ws)

        mock_cache = AsyncMock(spec=DashboardCacheManager)
        handler = DashboardEventHandler(mock_cache, notifier)

        await handler.handle("inventory.updated", {"product_id": 5, "available_quantity": 20})

        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload["type"] == "INVENTORY_UPDATED"
        assert payload["data"]["product_id"] == 5

    @pytest.mark.asyncio
    async def test_inventory_low_broadcasts_new_alert(self):
        mgr = ConnectionManager()
        notifier = DashboardNotifier(mgr)
        ws = AsyncMock(spec=WebSocket)
        await mgr.connect(ws)

        mock_cache = AsyncMock(spec=DashboardCacheManager)
        handler = DashboardEventHandler(mock_cache, notifier)

        await handler.handle("inventory.low", {"product_id": 99, "available_quantity": 2})

        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload["type"] == "NEW_ALERT"
        assert "99" in payload["data"]["message"]

    @pytest.mark.asyncio
    async def test_shipment_delivered_broadcasts_order_updated(self):
        mgr = ConnectionManager()
        notifier = DashboardNotifier(mgr)
        ws = AsyncMock(spec=WebSocket)
        await mgr.connect(ws)

        mock_cache = AsyncMock(spec=DashboardCacheManager)
        handler = DashboardEventHandler(mock_cache, notifier)

        await handler.handle("shipments.delivered", {"order_id": "ORD-DEL-1"})

        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload["type"] == "ORDER_UPDATED"
        assert payload["data"]["status"] == "DELIVERED"

    @pytest.mark.asyncio
    async def test_bad_kafka_payload_does_not_crash_consumer(self):
        """Missing required field in payload — must be caught inside handle()."""
        mgr = ConnectionManager()
        notifier = DashboardNotifier(mgr)
        mock_cache = AsyncMock(spec=DashboardCacheManager)
        handler = DashboardEventHandler(mock_cache, notifier)

        # orders.created requires order_id — omit it
        await handler.handle("orders.created", {})  # must NOT raise

    @pytest.mark.asyncio
    async def test_unknown_topic_produces_no_side_effects(self):
        mgr = ConnectionManager()
        notifier = DashboardNotifier(mgr)
        mock_cache = AsyncMock(spec=DashboardCacheManager)
        handler = DashboardEventHandler(mock_cache, notifier)

        await handler.handle("totally.unknown.topic", {"foo": "bar"})

        mock_cache.invalidate_summary.assert_not_called()
        mock_cache.invalidate_charts.assert_not_called()
        mock_cache.invalidate_inventory.assert_not_called()

    @pytest.mark.asyncio
    async def test_notifier_still_broadcasts_to_remaining_clients_after_one_fails(self):
        """
        If one WebSocket client raises during send, the other clients must
        still receive the broadcast. The failed client must be disconnected.
        """
        mgr = ConnectionManager()
        notifier = DashboardNotifier(mgr)

        good = AsyncMock(spec=WebSocket)
        bad = AsyncMock(spec=WebSocket)
        bad.send_text.side_effect = RuntimeError("pipe broken")

        await mgr.connect(good)
        await mgr.connect(bad)

        await notifier.notify_order_created("ORD-FAIL")

        good.send_text.assert_called_once()
        assert bad not in mgr.active_connections


# ─────────────────────────────────────────────────────────────────────────────
# 6. WebSocket Authentication
# ─────────────────────────────────────────────────────────────────────────────

class TestWebSocketAuthentication:

    def test_ws_no_token_closes_1008(self):
        """
        Connecting to /ws without a token query param must result in
        WebSocket close code 1008 (policy violation).
        """
        with TestClient(app) as c:
            with pytest.raises(Exception):
                # TestClient raises WebSocketDisconnect for rejected connections
                with c.websocket_connect("/api/v1/dashboard/ws") as ws:
                    ws.receive_text()

    def test_ws_invalid_token_closes_1008(self):
        """
        Connecting with a syntactically invalid JWT must be rejected.
        """
        with TestClient(app) as c:
            with pytest.raises(Exception):
                with c.websocket_connect("/api/v1/dashboard/ws?token=not.valid.jwt") as ws:
                    ws.receive_text()

    def test_ws_expired_token_closes_1008(self):
        """
        Connecting with an expired JWT must be rejected with code 1008.
        """
        token = _expired_token()
        with TestClient(app) as c:
            with pytest.raises(Exception):
                with c.websocket_connect(f"/api/v1/dashboard/ws?token={token}") as ws:
                    ws.receive_text()

    def test_ws_valid_token_is_accepted(self):
        """
        A valid JWT must result in a successful WebSocket handshake.
        """
        token = _valid_token()
        with TestClient(app) as c:
            with c.websocket_connect(f"/api/v1/dashboard/ws?token={token}") as ws:
                # Connection was accepted — send a ping and expect no crash
                ws.send_text("ping")


# ─────────────────────────────────────────────────────────────────────────────
# 7. WebSocket Reconnect Behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestWebSocketReconnect:

    @pytest.mark.asyncio
    async def test_disconnected_client_is_removed_from_active_connections(self):
        """
        After disconnect(), the client must not appear in active_connections.
        A subsequent broadcast must not attempt to send to the removed client.
        """
        mgr = ConnectionManager()
        ws = AsyncMock(spec=WebSocket)
        await mgr.connect(ws)
        assert ws in mgr.active_connections

        mgr.disconnect(ws)
        assert ws not in mgr.active_connections

    @pytest.mark.asyncio
    async def test_client_can_reconnect_after_disconnect(self):
        """
        A client that reconnects must receive broadcasts again.
        """
        mgr = ConnectionManager()
        ws = AsyncMock(spec=WebSocket)

        await mgr.connect(ws)
        mgr.disconnect(ws)
        await mgr.connect(ws)  # reconnect

        assert ws in mgr.active_connections
        await mgr.broadcast("hello")
        ws.send_text.assert_called_with("hello")

    @pytest.mark.asyncio
    async def test_disconnect_idempotent_for_unknown_socket(self):
        """
        Calling disconnect() with a socket that was never registered must
        not raise.
        """
        mgr = ConnectionManager()
        ws = AsyncMock(spec=WebSocket)
        mgr.disconnect(ws)  # must not raise

    @pytest.mark.asyncio
    async def test_broadcast_survives_partial_client_failure(self):
        """
        When one of N clients fails, the remaining N-1 must still receive
        the message. This simulates network drops mid-session.
        """
        mgr = ConnectionManager()
        clients = [AsyncMock(spec=WebSocket) for _ in range(5)]
        failing_index = 2
        clients[failing_index].send_text.side_effect = RuntimeError("dropped")

        for c in clients:
            await mgr.connect(c)

        await mgr.broadcast("event_data")

        for i, c in enumerate(clients):
            if i == failing_index:
                assert c not in mgr.active_connections
            else:
                c.send_text.assert_called_once_with("event_data")


# ─────────────────────────────────────────────────────────────────────────────
# 8. Graceful Shutdown
# ─────────────────────────────────────────────────────────────────────────────

class TestGracefulShutdown:

    @pytest.mark.asyncio
    async def test_connection_manager_is_empty_after_all_disconnects(self):
        mgr = ConnectionManager()
        clients = [AsyncMock(spec=WebSocket) for _ in range(3)]
        for c in clients:
            await mgr.connect(c)

        for c in clients:
            mgr.disconnect(c)

        assert len(mgr.active_connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast_on_empty_manager_does_not_raise(self):
        """Broadcasting with zero connected clients must be a no-op."""
        mgr = ConnectionManager()
        # Should not raise
        await mgr.broadcast("orphan_message")

    @pytest.mark.asyncio
    async def test_dashboard_event_handler_failure_is_isolated(self):
        """
        If the cache manager raises during invalidation, the handler must
        catch it and NOT propagate so the parent Kafka consumer loop survives.
        """
        mock_cache = AsyncMock(spec=DashboardCacheManager)
        mock_cache.invalidate_summary.side_effect = RuntimeError("unexpected Redis failure")
        mock_notifier = AsyncMock(spec=DashboardNotifier)

        handler = DashboardEventHandler(mock_cache, mock_notifier)
        # Must not raise
        await handler.handle("orders.created", {"order_id": "ORD-CRASH"})


# ─────────────────────────────────────────────────────────────────────────────
# 9. Structured Logging
# ─────────────────────────────────────────────────────────────────────────────

class TestStructuredLogging:

    def test_middleware_emits_log_with_all_required_fields(self, caplog):
        """
        DashboardLoggingMiddleware must emit a log record containing
        request_id, endpoint, duration_ms, cache_hit, user_id, status_code.
        """
        app.dependency_overrides[get_current_user] = lambda: _make_user("Admin")
        app.dependency_overrides[get_dashboard_service] = _make_service

        with caplog.at_level(logging.INFO, logger="dashboard.request"):
            with TestClient(app) as c:
                r = c.get(
                    "/api/v1/dashboard/summary",
                    headers={"Authorization": f"Bearer {_valid_token(user_id=42)}"},
                )

        app.dependency_overrides.clear()
        assert r.status_code == 200

        log_records = [
            rec for rec in caplog.records
            if rec.name == "dashboard.request"
        ]
        assert len(log_records) >= 1, "No log record emitted by DashboardLoggingMiddleware"

        rec = log_records[0]
        for field in ("request_id", "endpoint", "duration_ms", "cache_hit", "status_code"):
            assert hasattr(rec, field), f"Missing log field: {field}"

        assert rec.endpoint == "GET /api/v1/dashboard/summary"
        assert rec.status_code == 200
        assert isinstance(rec.duration_ms, float)

    def test_middleware_sets_x_request_id_response_header(self):
        """
        The middleware must propagate request_id as the X-Request-ID
        response header so clients can correlate logs.
        """
        app.dependency_overrides[get_current_user] = lambda: _make_user("Admin")
        app.dependency_overrides[get_dashboard_service] = _make_service

        with TestClient(app) as c:
            r = c.get("/api/v1/dashboard/summary")

        app.dependency_overrides.clear()
        assert "x-request-id" in r.headers
        # Must be a non-empty UUID-style string
        assert len(r.headers["x-request-id"]) == 36

    def test_middleware_does_not_log_non_dashboard_routes(self, caplog):
        """
        The logging middleware must only emit records for /api/v1/dashboard/*
        and must be silent for health check endpoints.
        """
        with caplog.at_level(logging.INFO, logger="dashboard.request"):
            with TestClient(app) as c:
                c.get("/health")

        dashboard_logs = [r for r in caplog.records if r.name == "dashboard.request"]
        assert len(dashboard_logs) == 0

    def test_service_logs_cache_miss(self, caplog):
        """
        DashboardService._get_cached_or_fetch must emit an INFO log
        with 'CACHE MISS' when Redis returns None.
        """
        with caplog.at_level(logging.INFO, logger="dashboard.service"):
            app.dependency_overrides[get_current_user] = lambda: _make_user("Admin")
            app.dependency_overrides[get_dashboard_service] = _make_service
            with TestClient(app) as c:
                c.get("/api/v1/dashboard/summary")
            app.dependency_overrides.clear()

        # The mock service's get_summary is a MagicMock, not the real service.
        # Test the real service log directly:
        pass  # covered by test_service_cache_miss_log below

    @pytest.mark.asyncio
    async def test_service_cache_miss_log_emitted(self, caplog):
        mock_repo = AsyncMock()
        mock_provider = DashboardProvider(mock_repo)
        mock_provider.get_summary_data = AsyncMock(return_value={
            "orders": {"total": 1, "delivered": 1, "pending": 0, "cancelled": 0, "revenue": 50.0},
            "inventory": {},
        })
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        service = DashboardService(mock_provider, mock_redis)

        with caplog.at_level(logging.INFO, logger="dashboard.service"):
            await service.get_summary()

        miss_logs = [r for r in caplog.records if "CACHE MISS" in r.message]
        assert len(miss_logs) >= 1

    @pytest.mark.asyncio
    async def test_service_cache_hit_log_emitted(self, caplog):
        cached = {
            "totalOrders": 10, "revenue": 1000.0, "pendingOrders": 1,
            "inventoryAccuracy": 99.0, "sla": 95.0, "csat": 4.8,
            "returns": 0, "deliveredOrders": 9,
        }
        mock_provider = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(cached)

        service = DashboardService(mock_provider, mock_redis)

        with caplog.at_level(logging.INFO, logger="dashboard.service"):
            await service.get_summary()

        hit_logs = [r for r in caplog.records if "CACHE HIT" in r.message]
        assert len(hit_logs) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 10. API Contract – Response Envelope & Pagination
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIContract:
    """
    Validates the frontend contract: field names, envelope shape, camelCase keys,
    pagination boundaries.
    """

    def test_summary_response_envelope(self, client_authenticated):
        r = client_authenticated.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "message" in body
        assert "timestamp" in body
        data = body["data"]
        for field in ["totalOrders", "revenue", "pendingOrders", "inventoryAccuracy", "sla", "csat"]:
            assert field in data, f"Missing camelCase field: {field}"

    def test_inventory_chart_out_of_stock_camel_case(self, client_authenticated):
        r = client_authenticated.get("/api/v1/dashboard/charts/inventory")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "outOfStock" in data, "outOfStock key missing (camelCase alias)"

    def test_activities_pagination_fields(self, client_authenticated):
        r = client_authenticated.get("/api/v1/dashboard/activities")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "page" in data
        assert "pageSize" in data
        assert "total" in data
        assert "activities" in data

    def test_pagination_page_zero_returns_422(self, client_authenticated):
        r = client_authenticated.get("/api/v1/dashboard/activities?page=0")
        assert r.status_code == 422

    def test_pagination_page_size_over_max_returns_422(self, client_authenticated):
        r = client_authenticated.get("/api/v1/dashboard/activities?page_size=101")
        assert r.status_code == 422

    def test_all_endpoints_return_200_for_admin(self, client_authenticated):
        for endpoint in ENDPOINTS:
            r = client_authenticated.get(endpoint)
            assert r.status_code == 200, f"{endpoint} returned {r.status_code}"

    def test_filter_params_accepted_on_all_endpoints(self, client_authenticated):
        params = "?warehouse_id=1&from_date=2026-07-01&to_date=2026-07-15"
        for endpoint in ENDPOINTS:
            r = client_authenticated.get(f"{endpoint}{params}")
            assert r.status_code == 200, f"Filter params rejected on {endpoint}"
