# tests/test_order_idor_security.py
"""
Security tests for Order IDOR (Insecure Direct Object Reference) vulnerability fix.
Tests cover:
  - Customer A views own order → 200
  - Customer A views Customer B's order → 403
  - Customer A cancels own order → success
  - Customer A cancels Customer B's order → 403
  - Admin views any order → 200
  - Admin cancels any order → success
  - Store Manager views any order → 200
  - Store Manager cancels any order → success
"""
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.modules.orders.service import OrderService
from app.core.exceptions import ForbiddenException, ResourceNotFoundException


def _make_mock_user(user_id: int, role_names: list[str]) -> MagicMock:
    """Create a mock User with the given ID and role names."""
    mock_user = MagicMock()
    mock_user.id = user_id
    roles = []
    for name in role_names:
        mock_role = MagicMock()
        mock_role.name = name
        roles.append(mock_role)
    mock_user.roles = roles
    return mock_user


@pytest_asyncio.fixture
async def setup_idor_test_data(db_session: AsyncSession):
    """
    Create a store, product, and two orders:
      - Order A belongs to customer_id=10 (Customer A)
      - Order B belongs to customer_id=20 (Customer B)
    """
    store = Store(
        name="IDOR Test Store", address="Addr", city="City",
        state="State", active=True, latitude=12.9716, longitude=77.5946
    )
    db_session.add(store)

    product = Product(sku="IDOR-P1", name="IDOR Product", category="C1", unit="pcs", active=True)
    db_session.add(product)
    await db_session.commit()

    order_a = Order(
        customer_id=10, store_id=store.id, status="PENDING",
        total_amount=50.00, payment_status="PENDING",
        latitude=12.9716, longitude=77.5946,
        sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    order_b = Order(
        customer_id=20, store_id=store.id, status="PENDING",
        total_amount=75.00, payment_status="PENDING",
        latitude=12.9716, longitude=77.5946,
        sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(order_a)
    db_session.add(order_b)
    await db_session.commit()

    item_a = OrderItem(order_id=order_a.id, product_id=product.id, quantity=1, price=50.00)
    item_b = OrderItem(order_id=order_b.id, product_id=product.id, quantity=1, price=75.00)
    db_session.add(item_a)
    db_session.add(item_b)
    await db_session.commit()

    return store, product, order_a, order_b


# ─── Customer A: View Own Order → 200 ───────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_views_own_order(db_session: AsyncSession, setup_idor_test_data):
    """Customer A (id=10) can view their own order."""
    _, _, order_a, _ = setup_idor_test_data
    service = OrderService(db_session)
    customer_a = _make_mock_user(10, ["Customer"])

    result = await service.get_order_by_id(order_a.id, current_user=customer_a)
    assert result.id == order_a.id
    assert result.customer_id == 10


# ─── Customer A: View Customer B's Order → 403 ──────────────────────────────

@pytest.mark.asyncio
async def test_customer_cannot_view_other_customer_order(db_session: AsyncSession, setup_idor_test_data):
    """Customer A (id=10) cannot view Customer B's order (customer_id=20)."""
    _, _, _, order_b = setup_idor_test_data
    service = OrderService(db_session)
    customer_a = _make_mock_user(10, ["Customer"])

    with pytest.raises(ForbiddenException):
        await service.get_order_by_id(order_b.id, current_user=customer_a)


# ─── Customer A: Cancel Own Order → Success ─────────────────────────────────

@pytest.mark.asyncio
async def test_customer_cancels_own_order(db_session: AsyncSession, setup_idor_test_data):
    """Customer A (id=10) can cancel their own order."""
    _, _, order_a, _ = setup_idor_test_data
    service = OrderService(db_session)
    customer_a = _make_mock_user(10, ["Customer"])

    result = await service.cancel_order(order_a.id, user_id=10, current_user=customer_a)
    assert result.status == "CANCELLED"
    assert result.payment_status == "REFUNDED"


# ─── Customer A: Cancel Customer B's Order → 403 ────────────────────────────

@pytest.mark.asyncio
async def test_customer_cannot_cancel_other_customer_order(db_session: AsyncSession, setup_idor_test_data):
    """Customer A (id=10) cannot cancel Customer B's order."""
    _, _, _, order_b = setup_idor_test_data
    service = OrderService(db_session)
    customer_a = _make_mock_user(10, ["Customer"])

    with pytest.raises(ForbiddenException):
        await service.cancel_order(order_b.id, user_id=10, current_user=customer_a)


# ─── Admin: View Any Order → 200 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_views_any_order(db_session: AsyncSession, setup_idor_test_data):
    """Admin can view any order regardless of customer_id."""
    _, _, order_a, order_b = setup_idor_test_data
    service = OrderService(db_session)
    admin = _make_mock_user(99, ["Admin"])

    result_a = await service.get_order_by_id(order_a.id, current_user=admin)
    assert result_a.id == order_a.id

    result_b = await service.get_order_by_id(order_b.id, current_user=admin)
    assert result_b.id == order_b.id


# ─── Admin: Cancel Any Order → Success ───────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_cancels_any_order(db_session: AsyncSession, setup_idor_test_data):
    """Admin can cancel any order."""
    _, _, order_a, _ = setup_idor_test_data
    service = OrderService(db_session)
    admin = _make_mock_user(99, ["Admin"])

    result = await service.cancel_order(order_a.id, user_id=99, current_user=admin)
    assert result.status == "CANCELLED"


# ─── Store Manager: View Any Order → 200 ────────────────────────────────────

@pytest.mark.asyncio
async def test_store_manager_views_any_order(db_session: AsyncSession, setup_idor_test_data):
    """Store Manager can view any order regardless of customer_id."""
    _, _, order_a, order_b = setup_idor_test_data
    service = OrderService(db_session)
    store_mgr = _make_mock_user(88, ["StoreManager"])

    result_a = await service.get_order_by_id(order_a.id, current_user=store_mgr)
    assert result_a.id == order_a.id

    result_b = await service.get_order_by_id(order_b.id, current_user=store_mgr)
    assert result_b.id == order_b.id


# ─── Store Manager: Cancel Any Order → Success ──────────────────────────────

@pytest.mark.asyncio
async def test_store_manager_cancels_any_order(db_session: AsyncSession, setup_idor_test_data):
    """Store Manager can cancel any order."""
    _, _, _, order_b = setup_idor_test_data
    service = OrderService(db_session)
    store_mgr = _make_mock_user(88, ["StoreManager"])

    result = await service.cancel_order(order_b.id, user_id=88, current_user=store_mgr)
    assert result.status == "CANCELLED"
