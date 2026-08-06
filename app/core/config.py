import os
from typing import List
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Accesco Living IMS"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS: configure production frontend origins with CORS_ORIGINS as a JSON list.
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Authentication rate limiting
    AUTH_LOGIN_RATE_LIMIT: int = 5
    AUTH_REGISTRATION_RATE_LIMIT: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/accesco_ims"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # Razorpay
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str

    # Replenishment Engine (ML Service)
    REPLENISHMENT_ENGINE_URL: str = "http://localhost:8000"
    REPLENISHMENT_ENGINE_TIMEOUT: int = 30

    # ETA Engine (ML Service)\
    ETA_ENGINE_URL: str = "http://localhost:8001"
    ETA_ENGINE_TIMEOUT: int = 30
    
    model_config = SettingsConfigDict(
        env_file=(".env.example", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
