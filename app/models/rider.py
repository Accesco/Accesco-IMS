
from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Boolean, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, validates
from app.models.base import Base, TimestampMixin
from datetime import datetime, timedelta
class Rider(Base, TimestampMixin):
    __tablename__ = "riders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)

    # State Machine Integration (Section 07)
    # Valid States: IDLE, ASSIGNED, EN_ROUTE_PICKUP, DELIVERING, RETURNING, BATCHING, OFFLINE
    status: Mapped[str] = mapped_column(String(30), default="IDLE", nullable=False)
    
    # RAE & Lifecycle Requirements (Section 03)
    battery_level: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    shift_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,default=lambda: datetime.utcnow() + timedelta(hours=8))    
    
    performance_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    # Failure & Decline Handling (Section 11)
    consecutive_declines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    @validates("status")
    def validate_status(self, key, value):
        valid_states = {"IDLE", "ASSIGNED", "EN_ROUTE_PICKUP", "DELIVERING", "RETURNING", "BATCHING", "OFFLINE"}
        if value not in valid_states:
            raise ValueError(f"Invalid state transition target: {value}")
        return value