"""
Dashboard Request Logging Middleware

Emits a single structured log entry per dashboard request containing:
  - request_id  (UUID, unique per request)
  - endpoint    (method + path)
  - duration_ms (total handler time in milliseconds)
  - cache_hit   (True/False, populated by DashboardService via request.state)
  - user_id     (decoded from JWT if present, else None)
  - status_code (HTTP response status)

Usage:
    app.add_middleware(DashboardLoggingMiddleware)

The middleware sets ``request.state.cache_hit = None`` before forwarding the
request so that service-layer code can flip it to True/False mid-flight.
"""

import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import decode_access_token

logger = logging.getLogger("dashboard.request")


class DashboardLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured per-request logging for all /dashboard routes.

    Adds ``request.state.request_id`` and ``request.state.cache_hit``
    so they can be read by downstream handlers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only log dashboard routes to avoid noise on unrelated paths
        if not request.url.path.startswith("/api/v1/dashboard"):
            return await call_next(request)

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.cache_hit = None  # service layer will set this

        # Extract user_id from bearer token without blocking on DB lookup
        user_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "dashboard_request",
            extra={
                "request_id": request_id,
                "endpoint": f"{request.method} {request.url.path}",
                "duration_ms": duration_ms,
                "cache_hit": request.state.cache_hit,
                "user_id": user_id,
                "status_code": response.status_code,
            },
        )

        # Propagate request_id in response for correlation
        response.headers["X-Request-ID"] = request_id

        return response
