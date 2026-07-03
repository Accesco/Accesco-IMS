
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Float, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin

# Import under TYPE_CHECKING to satisfy Pylance without circular loops [1.1.6, 1.1.9]
if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.community import Community


class ForecastMetric(Base, TimestampMixin):
    __tablename__ = "forecast_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    target_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    predicted_orders_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_rider_demand: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_batch_size: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_batch_window_sec: Mapped[int] = mapped_column(Integer, nullable=False)

    store: Mapped[Store] = relationship("Store", lazy="selectin")


class CommunityDynamicWindow(Base, TimestampMixin):
    __tablename__ = "community_dynamic_windows"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    community_id: Mapped[str] = mapped_column(ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    order_velocity_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    calculated_window_sec: Mapped[int] = mapped_column(Integer, nullable=False)

    community: Mapped[Community] = relationship("Community", lazy="selectin")