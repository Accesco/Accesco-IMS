import os
from typing import List
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Accesco Living IMS"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Security
    JWT_SECRET_KEY: str = "supersecretkeythatisverylongandsecurechangeinproduction"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/accesco_ims"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # Razorpay
    RAZORPAY_KEY_ID: str = "rzp_test_mockkeyid123"
    RAZORPAY_KEY_SECRET: str = "mockkeysecret456"
    RAZORPAY_WEBHOOK_SECRET: str = "mockwebhooksecret789"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
