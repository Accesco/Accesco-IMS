from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import redis_service
from app.core.kafka import kafka_producer
from app.core.exceptions import setup_exception_handlers
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize external services
    redis_service.connect()
    try:
        await kafka_producer.start()
    except Exception:
        # Log and continue so local development without Kafka running doesn't crash startup immediately
        pass
    yield
    # Shutdown: Clean up external connections
    await redis_service.disconnect()
    await kafka_producer.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Accesco Living Dark Store Inventory Management System (IMS)",
    version="1.0.0",
    lifespan=lifespan
)

# Global CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup custom exception handler mappings
setup_exception_handlers(app)

# Include main router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Health check endpoints
@app.get("/health", status_code=status.HTTP_200_OK, tags=["health"])
async def health_check():
    """Uptime health check."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}


@app.get("/health/db", status_code=status.HTTP_200_OK, tags=["health"])
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """Database connectivity health check."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


@app.get("/health/redis", status_code=status.HTTP_200_OK, tags=["health"])
async def redis_health_check():
    """Redis connectivity health check."""
    try:
        # Initialize client if not connected
        if not redis_service.client:
            redis_service.connect()
        await redis_service.client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": str(e)}


@app.get("/health/kafka", status_code=status.HTTP_200_OK, tags=["health"])
async def kafka_health_check():
    """Kafka connectivity health check."""
    if kafka_producer.producer is not None:
        return {"status": "healthy", "kafka": "connected"}
    else:
        return {"status": "unhealthy", "kafka": "disconnected"}
