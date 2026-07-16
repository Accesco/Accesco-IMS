"""
Tests for WebSocket infrastructure — connection, auth, events, cleanup.
"""

import os
import tempfile
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

import app.models  # noqa: F401
from app.main import app
from app.models.base import Base
from app.core.database import get_db
from app.core.security import create_access_token
from app.modules.websocket.manager import ConnectionManager, build_event_envelope

_DB_FD, _DB = tempfile.mkstemp(prefix="ims_ws_test_", suffix=".db")
os.close(_DB_FD)
_ENGINE = create_async_engine(f"sqlite+aiosqlite:///{_DB}", connect_args={"check_same_thread": False})
_SESSION = async_sessionmaker(bind=_ENGINE, class_=AsyncSession, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _SESSION() as session:
        yield session
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def http_client(db: AsyncSession):
    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _make_token(user_id: int = 1, roles: list = None) -> str:
    return create_access_token(subject=user_id, roles=roles or ["Admin"])


# ─── Event Envelope Tests ─────────────────────────────────────────────────────

class TestEventEnvelope:
    def test_build_event_envelope_structure(self):
        envelope = build_event_envelope(
            event_type="ORDER_CREATED",
            entity_type="order",
            entity_id=42,
            data={"order_id": 42, "status": "PENDING"},
        )
        assert envelope["event"] == "ORDER_CREATED"
        assert envelope["entity_type"] == "order"
        assert envelope["entity_id"] == "42"
        assert "timestamp" in envelope
        assert envelope["data"]["order_id"] == 42
        assert envelope["data"]["status"] == "PENDING"

    def test_build_event_envelope_custom_timestamp(self):
        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        envelope = build_event_envelope(
            event_type="TEST", entity_type="test", entity_id="1",
            data={}, timestamp=ts,
        )
        assert envelope["timestamp"] == ts.isoformat()


# ─── ConnectionManager Unit Tests ─────────────────────────────────────────────

class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        manager = ConnectionManager()
        ws = AsyncMock()
        ws.client_state = MagicMock()

        await manager.connect(ws, user_id=1, roles=["Admin"])
        assert manager.active_connection_count == 1

        await manager.disconnect(ws, user_id=1)
        assert manager.active_connection_count == 0

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self):
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect(ws1, user_id=1, roles=["Admin"])
        await manager.connect(ws2, user_id=1, roles=["Admin"])
        assert manager.active_connection_count == 2

        await manager.disconnect(ws1, user_id=1)
        assert manager.active_connection_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_delivers_to_all(self):
        from starlette.websockets import WebSocketState

        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, user_id=1, roles=["Admin"])
        await manager.connect(ws2, user_id=2, roles=["Viewer"])

        event = {"event": "TEST", "data": {}}
        await manager._deliver_to_local_clients(event)

        ws1.send_json.assert_called_once_with(event)
        ws2.send_json.assert_called_once_with(event)

        await manager.disconnect(ws1, user_id=1)
        await manager.disconnect(ws2, user_id=2)

    @pytest.mark.asyncio
    async def test_send_to_user_targets_specific_user(self):
        from starlette.websockets import WebSocketState

        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, user_id=1, roles=["Admin"])
        await manager.connect(ws2, user_id=2, roles=["Viewer"])

        event = {"event": "TARGETED", "data": {}}
        await manager.send_to_user(1, event)

        ws1.send_json.assert_called_once_with(event)
        ws2.send_json.assert_not_called()

        await manager.disconnect(ws1, user_id=1)
        await manager.disconnect(ws2, user_id=2)

    @pytest.mark.asyncio
    async def test_cleanup_dead_connections(self):
        from starlette.websockets import WebSocketState

        manager = ConnectionManager()
        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.send_json.side_effect = RuntimeError("Connection closed")

        await manager.connect(ws, user_id=1, roles=["Admin"])
        assert manager.active_connection_count == 1

        # Broadcasting to a dead connection should clean it up
        await manager._deliver_to_local_clients({"event": "TEST"})
        assert manager.active_connection_count == 0


# ─── WebSocket Route Tests (via TestClient) ───────────────────────────────────

class TestWebSocketRoute:
    @pytest.mark.asyncio
    async def test_connect_without_token_rejected(self, http_client):
        """Connection without token should be rejected."""
        from starlette.testclient import TestClient
        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws"):
                    pass

    @pytest.mark.asyncio
    async def test_connect_with_invalid_token_rejected(self, http_client):
        """Connection with invalid token should be rejected."""
        from starlette.testclient import TestClient
        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws?token=invalid_garbage_token"):
                    pass

    @pytest.mark.asyncio
    async def test_connect_with_valid_token(self, http_client):
        """Connection with valid JWT should succeed and respond to ping."""
        from starlette.testclient import TestClient
        token = _make_token(user_id=1, roles=["Admin"])
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws?token={token}") as ws:
                ws.send_text("ping")
                data = ws.receive_text()
                assert data == "pong"
