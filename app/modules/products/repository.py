from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate

class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_product_by_id(self, product_id: int) -> Optional[Product]:
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def get_product_by_sku(self, sku: str) -> Optional[Product]:
        result = await self.db.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    async def get_all_products(self, skip: int = 0, limit: int = 100) -> List[Product]:
        result = await self.db.execute(select(Product).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_product(self, product_data: ProductCreate) -> Product:
        db_product = Product(
            sku=product_data.sku,
            name=product_data.name,
            description=product_data.description,
            category=product_data.category,
            unit=product_data.unit,
            active=product_data.active
        )
        self.db.add(db_product)
        await self.db.flush()
        return db_product

    async def update_product(self, product: Product, update_data: ProductUpdate) -> Product:
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        await self.db.flush()
        return product
