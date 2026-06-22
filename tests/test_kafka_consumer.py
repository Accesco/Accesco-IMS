import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.store import Store
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.inventory import InventoryItem, InventoryReservation
from app.models.procurement import PurchaseOrder
from app.workers.kafka_consumer import process_message
from sqlalchemy.orm import selectinload

@asynccontextmanager
async def _noop_ctx(session: AsyncSession):
    """Yield session without closing it — lets the test fixture own the lifecycle."""
    yield session


@pytest_asyncio.fixture
async def setup_consumer_data(db_session: AsyncSession):
    # Create store
    store = Store(name="Consumer Store", address="Addr", city="City", state="State", active=True)
    db_session.add(store)
    
    # Create product
    product = Product(sku="C-PROD", name="Consumer Product", category="Cat", unit="pcs", active=True)
    db_session.add(product)
    await db_session.commit()
    
    # Setup inventory
    inv = InventoryItem(store_id=store.id, product_id=product.id, available_quantity=10, reserved_quantity=0, reorder_level=5)
    db_session.add(inv)
    
    # Setup order
    order = Order(customer_id=1, store_id=store.id, status="PENDING", total_amount=10.00, payment_status="PENDING")
    db_session.add(order)
    await db_session.commit()
    
    # Setup order item
    item = OrderItem(order_id=order.id, product_id=product.id, quantity=2, price=5.00)
    db_session.add(item)
    await db_session.commit()
    
    return store, product, order


@pytest.mark.asyncio
async def test_consumer_payment_confirmed(db_session: AsyncSession, setup_consumer_data):
    store, product, order = setup_consumer_data
    
    # Payload for payments.confirmed
    payload = {
        "order_id": order.id,
        "razorpay_order_id": "rzp_order_123",
        "razorpay_payment_id": "rzp_payment_456",
        "amount": 10.00
    }
    
    # Patch the session maker used by the worker to return our db_session
    async def mock_session_maker():
        return db_session
        
    with patch("app.workers.kafka_consumer.async_session_maker", lambda: _noop_ctx(db_session)):
        await process_message("payments.confirmed", payload)
        
    # Reload and verify order status
    await db_session.refresh(order)
    assert order.status == "CONFIRMED"
    assert order.payment_status == "COMPLETED"
    
    # Verify reservation was created
    result = await db_session.execute(
        select(InventoryReservation).where(InventoryReservation.order_id == str(order.id))
    )
    res = result.scalar_one_or_none()
    assert res is not None
    assert res.quantity == 2
    assert res.status == "PENDING"
    
    # Verify stock levels
    result = await db_session.execute(
        select(InventoryItem).where(
            InventoryItem.store_id == store.id,
            InventoryItem.product_id == product.id
        )
    )
    inv = result.scalar_one()
    # Available went from 10 to 8; reserved went from 0 to 2
    assert inv.available_quantity == 8
    assert inv.reserved_quantity == 2


@pytest.mark.asyncio
async def test_consumer_inventory_low(db_session: AsyncSession, setup_consumer_data):
    store, product, _ = setup_consumer_data
    
    payload = {
        "product_id": product.id,
        "available_quantity": 4,
        "reorder_level": 5
    }
    
    with patch("app.workers.kafka_consumer.async_session_maker", lambda: _noop_ctx(db_session)):
        await process_message("inventory.low", payload)
        
    # Verify draft PO was created (use selectinload to avoid async lazy-load on po.items)
    result = await db_session.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
    )
    pos = result.scalars().all()
    assert len(pos) == 1
    po = pos[0]
    assert po.status == "DRAFT"
    assert po.supplier_name == "AutoSupplier-Default"
    assert len(po.items) == 1
    assert po.items[0].product_id == product.id
    assert po.items[0].quantity == 100


@pytest.mark.asyncio
async def test_consumer_order_cancelled(db_session: AsyncSession, setup_consumer_data):
    store, product, order = setup_consumer_data
    
    # Setup a reservation first
    res = InventoryReservation(
        order_id=str(order.id),
        store_id=store.id,
        product_id=product.id,
        quantity=2,
        status="PENDING",
        expires_at=order.created_at  # placeholder
    )
    db_session.add(res)
    
    # Update inventory quantities to mimic active reservation
    result = await db_session.execute(
        select(InventoryItem).where(
            InventoryItem.store_id == store.id,
            InventoryItem.product_id == product.id
        )
    )
    inv = result.scalar_one()
    inv.available_quantity = 8
    inv.reserved_quantity = 2
    await db_session.commit()
    
    payload = {
        "order_id": order.id
    }
    
    with patch("app.workers.kafka_consumer.async_session_maker", lambda: _noop_ctx(db_session)):
        await process_message("orders.cancelled", payload)
        
    # Verify reservation released
    await db_session.refresh(res)
    assert res.status == "CANCELLED"
    
    # Verify inventory quantities restored
    await db_session.refresh(inv)
    assert inv.available_quantity == 10
    assert inv.reserved_quantity == 0
