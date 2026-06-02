from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.products.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.modules.products.service import ProductService

router = APIRouter(prefix="/products", tags=["products"])

# Role permission helpers
admin_or_procurement = RoleChecker(["Admin", "ProcurementManager"])
all_authorized = RoleChecker(["Admin", "StoreManager", "ProcurementManager", "InventoryManager", "Viewer"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_procurement)
):
    service = ProductService(db)
    return await service.create_product(product_data)


@router.get("", response_model=List[ProductResponse])
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = ProductService(db)
    return await service.get_all_products(skip, limit)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = ProductService(db)
    return await service.get_product_by_id(product_id)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    update_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_procurement)
):
    service = ProductService(db)
    return await service.update_product(product_id, update_data)
