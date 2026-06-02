from typing import Dict
from app.core.redis import RedisService

class CartRepository:
    def __init__(self, redis: RedisService):
        self.redis = redis

    async def get_cart(self, cart_id: str) -> Dict[str, int]:
        return await self.redis.get_cart(cart_id)

    async def add_to_cart(self, cart_id: str, product_id: int, quantity: int) -> None:
        await self.redis.add_to_cart(cart_id, str(product_id), quantity)

    async def set_cart_item(self, cart_id: str, product_id: int, quantity: int) -> None:
        await self.redis.set_cart_item(cart_id, str(product_id), quantity)

    async def remove_from_cart(self, cart_id: str, product_id: int) -> None:
        await self.redis.remove_from_cart(cart_id, str(product_id))

    async def clear_cart(self, cart_id: str) -> None:
        await self.redis.clear_cart(cart_id)
