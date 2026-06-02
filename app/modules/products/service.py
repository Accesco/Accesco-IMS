from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate
from app.models.product import Product
from app.core.exceptions import ResourceNotFoundException, IMSException

class ProductService:
    def __init__(self, db: AsyncSession):
        self.repo = ProductRepository(db)

    async def create_product(self, product_data: ProductCreate) -> Product:
        existing = await self.repo.get_product_by_sku(product_data.sku)
        if existing:
            raise IMSException(f"Product with SKU '{product_data.sku}' already exists", 400)
        return await self.repo.create_product(product_data)

    async def get_product_by_id(self, product_id: int) -> Product:
        product = await self.repo.get_product_by_id(product_id)
        if not product:
            raise ResourceNotFoundException(f"Product with ID {product_id} not found")
        return product

    async def get_all_products(self, skip: int = 0, limit: int = 100) -> List[Product]:
        return await self.repo.get_all_products(skip, limit)

    async def update_product(self, product_id: int, update_data: ProductUpdate) -> Product:
        product = await self.get_product_by_id(product_id)
        if update_data.sku:
            existing = await self.repo.get_product_by_sku(update_data.sku)
            if existing and existing.id != product_id:
                raise IMSException(f"Product with SKU '{update_data.sku}' already exists", 400)
        return await self.repo.update_product(product, update_data)
