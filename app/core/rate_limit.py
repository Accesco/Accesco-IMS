from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.redis import RedisService, get_redis


_INCREMENT_WITH_EXPIRY = """
local request_count = redis.call('INCR', KEYS[1])
if request_count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {request_count, redis.call('TTL', KEYS[1])}
"""


def _client_identifier(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def _enforce_limit(
    request: Request,
    scope: str,
    maximum_requests: int,
    redis: RedisService,
) -> None:
    key = f"rate-limit:auth:{scope}:{_client_identifier(request)}"
    redis_client = redis.client
    if redis_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis client unavailable.",
        )
    request_count, retry_after = await redis_client.eval(
        _INCREMENT_WITH_EXPIRY,
        1,
        key,
        settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )

    if request_count > maximum_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(max(retry_after, 1))},
        )


async def enforce_login_rate_limit(
    request: Request,
    redis: RedisService = Depends(get_redis),
) -> None:
    await _enforce_limit(request, "login", settings.AUTH_LOGIN_RATE_LIMIT, redis)


async def enforce_registration_rate_limit(
    request: Request,
    redis: RedisService = Depends(get_redis),
) -> None:
    await _enforce_limit(request, "registration", settings.AUTH_REGISTRATION_RATE_LIMIT, redis)
