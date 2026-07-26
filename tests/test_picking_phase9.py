import pytest
import asyncio
from httpx import AsyncClient
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime

from app.models.store import Store
from app.models.product import Product
from app.models.inventory import InventoryItem, InventoryReservation
from app.models.order import Order, OrderItem
from app.modules.inventory.service import InventoryService
from app.modules.orders.service import OrderService
from app.workers.kafka_consumer import process_message

pytestmark = pytest.mark.asyncio

async def create_test_data(db_session: AsyncSession):
    store = Store(name="Test Store Phase 9", address="123", city="NY", state="NY")
    product = Product(name="Test Prod", sku="SKU999", description="Desc", category="Test", unit="unit")
    db_session.add(store)
    db_session.add(product)
    await db_session.flush()

    item = InventoryItem(store_id=store.id, product_id=product.id, available_quantity=10, reserved_quantity=0, reorder_level=2)
    db_session.add(item)
    await db_session.flush()

    order = Order(
        customer_id=1, store_id=store.id, status="PENDING", total_amount=10.0, 
        payment_status="PENDING", delivery_zone="A", assignment_status="UNASSIGNED",
        latitude=0.0, longitude=0.0, sla_deadline=datetime.now()
    )
    db_session.add(order)
    await db_session.flush()
    
    order_item = OrderItem(order_id=order.id, product_id=product.id, quantity=5, price=10.0)
    db_session.add(order_item)
    
    order2 = Order(
        customer_id=1, store_id=store.id, status="PENDING", total_amount=10.0, 
        payment_status="PENDING", delivery_zone="A", assignment_status="UNASSIGNED",
        latitude=0.0, longitude=0.0, sla_deadline=datetime.now()
    )
    db_session.add(order2)
    await db_session.flush()
    
    order_item2 = OrderItem(order_id=order2.id, product_id=product.id, quantity=8, price=10.0)
    db_session.add(order_item2)

    await db_session.commit()
    return store, product, item, order, order2

async def test_concurrent_allocation_overselling(db_session: AsyncSession):
    """
    Test that two concurrent allocations for different orders trying to reserve 
    the same limited inventory will not oversell.
    Available: 10
    Order 1 needs 5. Order 2 needs 8.
    They cannot both succeed (5+8 = 13 > 10).
    """
    store, product, item, order, order2 = await create_test_data(db_session)
    
    service = OrderService(db_session)
    await db_session.execute(text("UPDATE orders SET status='CONFIRMED' WHERE id IN (:id1, :id2)"), {"id1": order.id, "id2": order2.id})
    await db_session.commit()
    
    # Run first allocation
    try:
        await service.allocate_order(order.id, user_id=1)
        first_success = True
    except Exception:
        first_success = False

    # Run second allocation
    try:
        await service.allocate_order(order2.id, user_id=1)
        second_success = True
    except Exception as e:
        assert "Insufficient stock" in str(e)
        second_success = False

    # One should succeed, one should fail
    assert first_success == True
    assert second_success == False
    
    # Verify inventory is correct
    result = await db_session.execute(select(InventoryItem).where(InventoryItem.product_id == product.id))
    inv = result.scalar_one()
    # 5 was reserved (5 avail left)
    assert inv.available_quantity == 5
    assert inv.reserved_quantity == 5

async def test_duplicate_kafka_idempotency(db_session: AsyncSession):
    """
    Test that duplicate payments.confirmed events don't create double reservations.
    """
    store, product, item, order, _ = await create_test_data(db_session)
    
    order_id = str(order.id)
    payload = {"order_id": order.id}
    
    from unittest.mock import patch
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session():
        yield db_session
    
    # Process first time
    with patch("app.workers.kafka_consumer.async_session_maker", side_effect=mock_session):
        await process_message("payments.confirmed", payload)
    
    # Verify reservation created
    result = await db_session.execute(select(InventoryReservation).where(InventoryReservation.order_id == order_id))
    reservations = result.scalars().all()
    assert len(reservations) == 1
    assert reservations[0].quantity == 5
        
    # Process second time (Duplicate)
    with patch("app.workers.kafka_consumer.async_session_maker", side_effect=mock_session):
        await process_message("payments.confirmed", payload)
    
    # Verify no new reservations were created
    result = await db_session.execute(select(InventoryReservation).where(InventoryReservation.order_id == order_id))
    reservations = result.scalars().all()
    assert len(reservations) == 1  # Still 1!

async def test_atomic_allocation_rollback(db_session: AsyncSession):
    """
    Test that if an order has multiple items and one fails, the whole allocation rolls back.
    """
    store, product, item, order, _ = await create_test_data(db_session)
    
    # Add a second item to the order that exceeds inventory
    product2 = Product(name="Test Prod 2", sku="SKU999_2", description="Desc", category="Test", unit="unit")
    db_session.add(product2)
    await db_session.flush()

    item2 = InventoryItem(store_id=store.id, product_id=product2.id, available_quantity=2, reserved_quantity=0, reorder_level=2)
    db_session.add(item2)
    await db_session.flush()
    
    product_id = product.id
    order_item2 = OrderItem(order_id=order.id, product_id=product2.id, quantity=10, price=10.0) # Quantity 10, but only 2 available
    db_session.add(order_item2)
    
    order_id = str(order.id)
    order.status = "CONFIRMED"
    await db_session.commit()
    
    service = OrderService(db_session)
    try:
        await service.allocate_order(int(order_id))
        assert False, "Should have raised insufficient stock exception"
    except Exception as e:
        assert "Insufficient stock" in str(e)
        
    await db_session.rollback()
    
    # Verify NO reservations were created (the first item should have rolled back)
    result = await db_session.execute(select(InventoryReservation).where(InventoryReservation.order_id == order_id))
    reservations = result.scalars().all()
    assert len(reservations) == 0
    
    # Verify inventory was not deducted
    result = await db_session.execute(select(InventoryItem).where(InventoryItem.product_id == product_id))
    inv = result.scalar_one()
    assert inv.available_quantity == 10
