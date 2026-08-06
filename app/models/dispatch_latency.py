# app/models/dispatch_latency.py
from __future__ import annotations

from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class DispatchLatencySample(Base, TimestampMixin):
    """
   Per-request latency samples for P50/P95/P99 percentile computation.
    """
    __tablename__ = "dispatch_latency_samples"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # The route path that was timed, e.g. "/dispatch/assign"
    path: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
