import asyncio
import logging
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.auth import User, Role
from app.models.store import Store
from app.models.product import Product
from app.models.inventory import InventoryItem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("db_seeder")

ROLES = [
    {"name": "Admin", "description": "Administrator with full system privileges"},
    {"name": "StoreManager", "description": "Manager of specific dark stores"},
    {"name": "ProcurementManager", "description": "Responsible for managing purchase orders and suppliers"},
    {"name": "InventoryManager", "description": "Responsible for dark store stock levels"},
    {"name": "Viewer", "description": "Read-only access to IMS dashboard"}
]

STORES = [
    {
        "name": "Delhi Central",
        "address": "Connaught Place, Block E",
        "city": "New Delhi",
        "state": "Delhi",
        "active": True
    },
    {
        "name": "Gurgaon East",
        "address": "Sector 45, Near Huda City Center",
        "city": "Gurugram",
        "state": "Haryana",
        "active": True
    }
]

PRODUCTS = [
    {"sku": "MILK-AMUL-1L", "name": "Amul Taaza Milk 1L", "description": "Fresh pasteurized toned milk", "category": "Dairy", "unit": "pack"},
    {"sku": "BREAD-BRIT-WHT", "name": "Britannia White Bread 400g", "description": "Soft sliced white bread", "category": "Bakery", "unit": "pack"},
    {"sku": "BUTTER-AMUL-100G", "name": "Amul Butter 100g", "description": "Salted butter made from cow milk", "category": "Dairy", "unit": "pack"},
    {"sku": "EGGS-FARM-12PC", "name": "Farm Fresh Eggs 12 Pack", "description": "High-protein farm-fresh brown eggs", "category": "Dairy & Eggs", "unit": "box"},
    {"sku": "COKE-500ML", "name": "Coca-Cola 500ml", "description": "Sparkling soft drink", "category": "Beverages", "unit": "bottle"},
    {"sku": "CHOC-CAD-DAIRY", "name": "Cadbury Dairy Milk 50g", "description": "Smooth milk chocolate bar", "category": "Snacks & Sweets", "unit": "bar"},
    {"sku": "CHIPS-LAYS-SLT", "name": "Lays Classic Salted 50g", "description": "Crispy potato chips classic salted", "category": "Snacks & Sweets", "unit": "pack"},
    {"sku": "WATER-BISL-1L", "name": "Bisleri Mineral Water 1L", "description": "Purified mineral drinking water", "category": "Beverages", "unit": "bottle"},
    {"sku": "RICE-BASM-5KG", "name": "India Gate Basmati Rice 5kg", "description": "Premium long-grain basmati rice", "category": "Staples", "unit": "bag"},
    {"sku": "OIL-FORT-1L", "name": "Fortune Mustard Oil 1L", "description": "Pure cold-pressed mustard oil", "category": "Staples", "unit": "bottle"}
]

async def seed_data() -> None:
    async with async_session_maker() as session:
        try:
            logger.info("Starting database seeding...")

            # 1. Seed Roles
            db_roles = {}
            for r_data in ROLES:
                result = await session.execute(select(Role).where(Role.name == r_data["name"]))
                role = result.scalar_one_or_none()
                if not role:
                    role = Role(name=r_data["name"], description=r_data["description"])
                    session.add(role)
                    await session.flush()
                    logger.info(f"Seeded Role: {role.name}")
                db_roles[role.name] = role

            # 2. Seed Admin User
            result = await session.execute(select(User).where(User.username == "admin"))
            admin_user = result.scalar_one_or_none()
            if not admin_user:
                hashed_pw = get_password_hash("adminpassword")
                admin_user = User(
                    username="admin",
                    email="admin@accesco.com",
                    hashed_password=hashed_pw,
                    roles=[db_roles["Admin"]],
                    is_active=True
                )
                session.add(admin_user)
                await session.flush()
                logger.info("Seeded Admin User: admin (pw: adminpassword)")

            # 3. Seed Stores
            db_stores = []
            for s_data in STORES:
                result = await session.execute(select(Store).where(Store.name == s_data["name"]))
                store = result.scalar_one_or_none()
                if not store:
                    store = Store(
                        name=s_data["name"],
                        address=s_data["address"],
                        city=s_data["city"],
                        state=s_data["state"],
                        active=s_data["active"]
                    )
                    session.add(store)
                    await session.flush()
                    logger.info(f"Seeded Store: {store.name}")
                db_stores.append(store)

            # 4. Seed Products
            db_products = []
            for p_data in PRODUCTS:
                result = await session.execute(select(Product).where(Product.sku == p_data["sku"]))
                product = result.scalar_one_or_none()
                if not product:
                    product = Product(
                        sku=p_data["sku"],
                        name=p_data["name"],
                        description=p_data["description"],
                        category=p_data["category"],
                        unit=p_data["unit"],
                        active=True
                    )
                    session.add(product)
                    await session.flush()
                    logger.info(f"Seeded Product SKU: {product.sku}")
                db_products.append(product)

            # 5. Seed Inventory items (Associate each product with each store)
            for store in db_stores:
                for product in db_products:
                    result = await session.execute(
                        select(InventoryItem).where(
                            InventoryItem.store_id == store.id,
                            InventoryItem.product_id == product.id
                        )
                    )
                    inv_item = result.scalar_one_or_none()
                    if not inv_item:
                        inv_item = InventoryItem(
                            store_id=store.id,
                            product_id=product.id,
                            available_quantity=100,  # 100 items available initially
                            reserved_quantity=0,
                            reorder_level=10         # Alert at 10 items
                        )
                        session.add(inv_item)
                        logger.info(f"Seeded Inventory for Store {store.name} and Product {product.sku}")
            
            await session.commit()
            logger.info("Database seeding completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during seeding: {e}")
            await session.rollback()
            raise e

if __name__ == "__main__":
    asyncio.run(seed_data())
