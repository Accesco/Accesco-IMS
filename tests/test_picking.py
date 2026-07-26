import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.auth import User, Role
from app.models.store import Store
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.core.security import get_password_hash

@pytest_asyncio.fixture(scope="function")
async def setup_picking_data(db_session: AsyncSession):
    # Create Roles
    admin_role = Role(name="Admin", description="Admin")
    staff_role = Role(name="WarehouseStaff", description="Staff")
    db_session.add_all([admin_role, staff_role])
    await db_session.flush()

    # Create Users
    admin_user = User(
        username="admin_pick",
        email="admin_pick@test.com",
        hashed_password=get_password_hash("pass"),
        roles=[admin_role],
        is_active=True
    )
    staff_user = User(
        username="staff_pick",
        email="staff_pick@test.com",
        hashed_password=get_password_hash("pass"),
        roles=[staff_role],
        is_active=True
    )
    db_session.add_all([admin_user, staff_user])
    await db_session.flush()

    # Create Store
    store = Store(name="Test Store", address="123", city="Test", state="Test", active=True)
    db_session.add(store)
    await db_session.flush()

    # Create Product
    product = Product(sku="TEST-1", name="Test Prod", description="Test", category="Test", unit="pc", active=True)
    db_session.add(product)
    await db_session.flush()

    from datetime import datetime, timezone
    order = Order(
        customer_id=admin_user.id,
        store_id=store.id,
        status="CONFIRMED",
        payment_status="COMPLETED",
        total_amount=100.0,
        latitude=0.0,
        longitude=0.0,
        delivery_zone="ZONE_A",
        sla_deadline=datetime.now(timezone.utc)
    )
    db_session.add(order)
    await db_session.flush()

    # Create OrderItem
    order_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=5,
        price=20.0
    )
    db_session.add(order_item)
    await db_session.commit()

    return {
        "admin_user": admin_user,
        "staff_user": staff_user,
        "store": store,
        "product": product,
        "order": order,
        "order_item": order_item
    }

@pytest.mark.asyncio
async def test_picking_flow(client: TestClient, setup_picking_data):
    data = setup_picking_data
    store = data["store"]
    admin = data["admin_user"]
    staff = data["staff_user"]
    
    # Authenticate as Admin
    login_resp = client.post("/api/v1/auth/login", json={"username": admin.username, "password": "pass"})
    admin_token = login_resp.json()["access_token"]
    
    # Authenticate as Staff
    login_resp2 = client.post("/api/v1/auth/login", json={"username": staff.username, "password": "pass"})
    staff_token = login_resp2.json()["access_token"]

    # 1. Generate Wave
    resp = client.post(
        f"/api/v1/picking/waves/generate?store_id={store.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    wave = resp.json()
    assert wave["store_id"] == store.id
    
    # 2. Get Tasks for the wave
    resp = client.get(
        f"/api/v1/picking/tasks?wave_id={wave['id']}",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["status"] == "PENDING"
    assert len(task["items"]) == 1
    
    task_id = task["id"]
    item_id = task["items"][0]["id"]
    
    # 3. Assign Task
    resp = client.post(
        f"/api/v1/picking/tasks/{task_id}/assign",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"
    assert resp.json()["assigned_to"] == staff.id
    
    # 4. Pick Item
    resp = client.post(
        f"/api/v1/picking/tasks/{task_id}/items/{item_id}/pick",
        json={"quantity": 5},
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["picked_quantity"] == 5
    
    # 5. Complete Task
    resp = client.post(
        f"/api/v1/picking/tasks/{task_id}/complete",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"
