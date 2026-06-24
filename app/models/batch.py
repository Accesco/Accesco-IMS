# app/models/batch.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.rider import Rider


class Batch(Base, TimestampMixin):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    community_id: Mapped[str] = mapped_column(ForeignKey("communities.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    
    rider_id: Mapped[Optional[int]] = mapped_column(ForeignKey("riders.id"), nullable=True)
    offered_rider_id: Mapped[Optional[int]] = mapped_column(ForeignKey("riders.id"), nullable=True)
    
    dispatch_by: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assignment_offered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    orders: Mapped[List[Order]] = relationship("Order", back_populates="batch")
    rider: Mapped[Optional[Rider]] = relationship("Rider", foreign_keys=[rider_id])
    offered_rider: Mapped[Optional[Rider]] = relationship("Rider", foreign_keys=[offered_rider_id])