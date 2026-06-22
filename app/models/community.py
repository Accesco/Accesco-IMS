from __future__ import annotations

from sqlalchemy import String, Float, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class Community(Base, TimestampMixin):
    __tablename__ = "communities"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    centroid_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    polygon: Mapped[dict] = mapped_column(JSON, nullable=False)
    entry_points: Mapped[dict] = mapped_column(JSON, nullable=False)
    avg_walk_time_min: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    batch_window_sec: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    max_batch_size: Mapped[int] = mapped_column(Integer, default=4, nullable=False)