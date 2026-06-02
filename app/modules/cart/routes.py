from fastapi import APIRouter, Depends, status
from typing import Dict

from app.core.redis import RedisService, get_redis
from app.modules.auth.routes import get_current_user
from app.models.auth import User
from app.modules.cart.schemas import CartItem, CartResponse
from app.modules.cart.service import CartService

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    redis: RedisService = Depends(get_redis)
):
    service = CartService(redis)
    cart_id = f"user_{current_user.id}"
    items = await service.get_cart(cart_id)
    return CartResponse(cart_id=cart_id, items=items)


@router.post("/items", response_model=CartResponse)
async def add_to_cart(
    item: CartItem,
    current_user: User = Depends(get_current_user),
    redis: RedisService = Depends(get_redis)
):
    service = CartService(redis)
    cart_id = f"user_{current_user.id}"
    items = await service.add_to_cart(cart_id, item.product_id, item.quantity)
    return CartResponse(cart_id=cart_id, items=items)


@router.put("/items", response_model=CartResponse)
async def update_cart_item(
    item: CartItem,
    current_user: User = Depends(get_current_user),
    redis: RedisService = Depends(get_redis)
):
    service = CartService(redis)
    cart_id = f"user_{current_user.id}"
    items = await service.set_cart_item(cart_id, item.product_id, item.quantity)
    return CartResponse(cart_id=cart_id, items=items)


@router.delete("/items/{product_id}", response_model=CartResponse)
async def remove_from_cart(
    product_id: int,
    current_user: User = Depends(get_current_user),
    redis: RedisService = Depends(get_redis)
):
    service = CartService(redis)
    cart_id = f"user_{current_user.id}"
    items = await service.remove_from_cart(cart_id, product_id)
    return CartResponse(cart_id=cart_id, items=items)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    redis: RedisService = Depends(get_redis)
):
    service = CartService(redis)
    cart_id = f"user_{current_user.id}"
    await service.clear_cart(cart_id)
