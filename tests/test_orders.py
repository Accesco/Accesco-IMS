# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.store import Store
from app.models.product import Product
from app.models.order import Order
from app.models.outbox import OutboxEvent
from app.modules.orders.service import OrderService
from app.modules.orders.schemas import OrderCreate, OrderItemCreate

@pytest_asyncio.fixture
async def setup_test_data(db_session: AsyncSession):
    # Create Store
    store = Store(name="Order Store", address="Addr", city="City", state="State", active=True, latitude=12.9716, longitude=77.5946)
    db_session.add(store)
    
    # Create Products
    p1 = Product(sku="P1", name="Product 1", category="C1", unit="pcs", active=True)
    p2 = Product(sku="P2", name="Product 2", category="C2", unit="pcs", active=True)
    db_session.add(p1)
    db_session.add(p2)
    
    await db_session.commit()
    return store, p1, p2


@pytest.mark.asyncio
async def test_place_order(db_session: AsyncSession, setup_test_data):
    store, p1, p2 = setup_test_data
    service = OrderService(db_session)
    
    order_data = OrderCreate(
        store_id=store.id,
        items=[
            OrderItemCreate(product_id=p1.id, quantity=2, price=10.50),
            OrderItemCreate(product_id=p2.id, quantity=1, price=20.00)
        ],
        latitude=12.9716,
        longitude=77.5946
    )
    
    # Place order
    order = await service.place_order(order_data, customer_id=42)
    
    # Assertions
    assert order.id is not None
    assert order.customer_id == 42
    assert order.store_id == store.id
    # (2 * 10.50) + (1 * 20.00) = 41.00
    assert float(order.total_amount) == 41.00
    assert order.status == "PENDING"
    assert len(order.items) == 2
    
    # Verify that an orders.placed event was written to the outbox
    result = await db_session.execute(
        select(OutboxEvent).where(OutboxEvent.event_type == "orders.placed")
    )
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.status == "PENDING"
    assert event.payload["order_id"] == order.id
    assert event.payload["customer_id"] == 42
    assert event.payload["total_amount"] == 41.00
