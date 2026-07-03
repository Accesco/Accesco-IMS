# app/models/rider.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Boolean, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, validates
from app.models.base import Base, TimestampMixin

class Rider(Base, TimestampMixin):
    __tablename__ = "riders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="IDLE", nullable=False)
    battery_level: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    performance_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    consecutive_declines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Shift Lifecycle Columns (Section 03)
    shift_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shift_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @validates("status")
    def validate_status(self, key, value):
        valid_states = {"IDLE", "ASSIGNED", "EN_ROUTE_PICKUP", "DELIVERING", "RETURNING", "BATCHING", "OFFLINE"}
        if value not in valid_states:
            raise ValueError(f"Invalid state transition target: {value}")
        return value