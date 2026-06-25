# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.inventory.service import InventoryService
from app.modules.inventory.schemas import InventoryReservationCreate, InventoryItemCreate
from app.models.store import Store
from app.models.product import Product
from app.models.inventory import InventoryItem, InventoryReservation
from app.core.exceptions import IMSException

@pytest_asyncio.fixture
async def setup_store_and_product(db_session: AsyncSession):
    # Setup Store
    store = Store(name="Test Store", address="Test Addr", city="Test City", state="Test State", active=True)
    db_session.add(store)
    
    # Setup Product
    product = Product(sku="TEST-SKU", name="Test Product", category="Test Category", unit="pcs", active=True)
    db_session.add(product)
    
    await db_session.commit()
    
    # Setup Inventory Item
    inv_item = InventoryItem(
        store_id=store.id,
        product_id=product.id,
        available_quantity=50,
        reserved_quantity=0,
        reorder_level=5
    )
    db_session.add(inv_item)
    await db_session.commit()
    
    return store, product, inv_item


@pytest.mark.asyncio
async def test_add_stock(db_session: AsyncSession, setup_store_and_product):
    store, product, _ = setup_store_and_product
    service = InventoryService(db_session)
    
    # Add stock
    updated_item = await service.add_stock(store.id, product.id, 20)
    assert updated_item.available_quantity == 70


@pytest.mark.asyncio
async def test_reserve_stock_success(db_session: AsyncSession, setup_store_and_product):
    store, product, _ = setup_store_and_product
    service = InventoryService(db_session)
    
    res_data = InventoryReservationCreate(
        store_id=store.id,
        product_id=product.id,
        quantity=10,
        order_id="test_order_123",
        expires_in_seconds=300
    )
    
    # Act
    reservation = await service.reserve_stock(res_data)
    
    # Assert
    assert reservation.quantity == 10
    assert reservation.status == "PENDING"
    
    # Reload inventory item from db
    await db_session.refresh(reservation.store)
    db_item = await service.repo.get_item_by_store_and_product(store.id, product.id)
    assert db_item.available_quantity == 40
    assert db_item.reserved_quantity == 10


@pytest.mark.asyncio
async def test_reserve_stock_insufficient_fails(db_session: AsyncSession, setup_store_and_product):
    store, product, _ = setup_store_and_product
    service = InventoryService(db_session)
    
    res_data = InventoryReservationCreate(
        store_id=store.id,
        product_id=product.id,
        quantity=60,  # exceeds available 50
        order_id="test_order_123",
        expires_in_seconds=300
    )
    
    # Act & Assert
    with pytest.raises(IMSException):
        await service.reserve_stock(res_data)
        
    # Check that stock was not modified
    db_item = await service.repo.get_item_by_store_and_product(store.id, product.id)
    assert db_item.available_quantity == 50
    assert db_item.reserved_quantity == 0


@pytest.mark.asyncio
async def test_confirm_reservation(db_session: AsyncSession, setup_store_and_product):
    store, product, _ = setup_store_and_product
    service = InventoryService(db_session)
    
    res_data = InventoryReservationCreate(
        store_id=store.id,
        product_id=product.id,
        quantity=10,
        order_id="test_order_123",
        expires_in_seconds=300
    )
    reservation = await service.reserve_stock(res_data)
    
    # Act
    confirmed_res = await service.confirm_reservation(reservation.id)
    assert confirmed_res.status == "COMPLETED"
    
    # Verify stock levels
    db_item = await service.repo.get_item_by_store_and_product(store.id, product.id)
    # Available remains 40 (was decremented during reservation), reserved goes back to 0
    assert db_item.available_quantity == 40
    assert db_item.reserved_quantity == 0


@pytest.mark.asyncio
async def test_release_reservation(db_session: AsyncSession, setup_store_and_product):
    store, product, _ = setup_store_and_product
    service = InventoryService(db_session)
    
    res_data = InventoryReservationCreate(
        store_id=store.id,
        product_id=product.id,
        quantity=10,
        order_id="test_order_123",
        expires_in_seconds=300
    )
    reservation = await service.reserve_stock(res_data)
    
    # Act
    cancelled_res = await service.release_reservation(reservation.id)
    assert cancelled_res.status == "CANCELLED"
    
    # Verify stock levels are restored
    db_item = await service.repo.get_item_by_store_and_product(store.id, product.id)
    assert db_item.available_quantity == 50
    assert db_item.reserved_quantity == 0
