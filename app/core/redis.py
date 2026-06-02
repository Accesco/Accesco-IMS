import json
from typing import Optional, Dict, Any
import redis.asyncio as redis
from app.core.config import settings

class RedisService:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    def connect(self) -> None:
        self.client = redis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self) -> None:
        if self.client:
            await self.client.close()
            self.client = None

    async def get(self, key: str) -> Optional[str]:
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        return await self.client.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> None:
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        await self.client.delete(key)

    # Cart helper methods
    async def get_cart(self, cart_id: str) -> Dict[str, int]:
        """
        Gets cart content. Returns dict mapping product_id (str) -> quantity (int).
        """
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        cart_key = f"cart:{cart_id}"
        items = await self.client.hgetall(cart_key)
        return {k: int(v) for k, v in items.items()}

    async def add_to_cart(self, cart_id: str, product_id: str, quantity: int) -> None:
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        cart_key = f"cart:{cart_id}"
        await self.client.hincrby(cart_key, product_id, quantity)
        # Set TTL to 7 days for inactive carts
        await self.client.expire(cart_key, 604800)

    async def set_cart_item(self, cart_id: str, product_id: str, quantity: int) -> None:
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        cart_key = f"cart:{cart_id}"
        if quantity <= 0:
            await self.client.hdel(cart_key, product_id)
        else:
            await self.client.hset(cart_key, product_id, quantity)
            await self.client.expire(cart_key, 604800)

    async def remove_from_cart(self, cart_id: str, product_id: str) -> None:
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        cart_key = f"cart:{cart_id}"
        await self.client.hdel(cart_key, product_id)

    async def clear_cart(self, cart_id: str) -> None:
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        cart_key = f"cart:{cart_id}"
        await self.client.delete(cart_key)

    # Distributed locking helper for inventory checks
    async def acquire_lock(self, lock_name: str, acquire_timeout: int = 5, lock_timeout: int = 10) -> bool:
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        lock_key = f"lock:{lock_name}"
        return bool(await self.client.set(lock_key, "locked", ex=lock_timeout, nx=True))

    async def release_lock(self, lock_name: str) -> None:
        if not self.client:
            raise RuntimeError("Redis client is not initialized")
        lock_key = f"lock:{lock_name}"
        await self.client.delete(lock_key)


redis_service = RedisService(settings.REDIS_URL)


# Dependency injection helper
async def get_redis() -> RedisService:
    if redis_service.client is None:
        redis_service.connect()
    return redis_service
