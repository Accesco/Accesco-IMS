from typing import Dict
from app.core.redis import RedisService
from app.modules.cart.repository import CartRepository

class CartService:
    def __init__(self, redis: RedisService):
        self.repo = CartRepository(redis)

    async def get_cart(self, cart_id: str) -> Dict[str, int]:
        return await self.repo.get_cart(cart_id)

    async def add_to_cart(self, cart_id: str, product_id: int, quantity: int) -> Dict[str, int]:
        await self.repo.add_to_cart(cart_id, product_id, quantity)
        return await self.repo.get_cart(cart_id)

    async def set_cart_item(self, cart_id: str, product_id: int, quantity: int) -> Dict[str, int]:
        await self.repo.set_cart_item(cart_id, product_id, quantity)
        return await self.repo.get_cart(cart_id)

    async def remove_from_cart(self, cart_id: str, product_id: int) -> Dict[str, int]:
        await self.repo.remove_from_cart(cart_id, product_id)
        return await self.repo.get_cart(cart_id)

    async def clear_cart(self, cart_id: str) -> None:
        await self.repo.clear_cart(cart_id)
