
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import String, Numeric, ForeignKey, Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.product import Product

if TYPE_CHECKING:
    from app.models.rider import Rider
    from app.models.batch import Batch


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)

    # Coordinates of Delivery Location
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Zone Metrics (Section 04)
    delivery_zone: Mapped[str] = mapped_column(String(20), default="ZONE_A", nullable=False)
    sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Community Flow Batching Attributes (Section 05)
    community_id: Mapped[Optional[str]] = mapped_column(ForeignKey("communities.id"), nullable=True)
    batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("batches.id"), nullable=True)

    # Rider Assignment Engine Attributes (Section 03)
    rider_id: Mapped[Optional[int]] = mapped_column(ForeignKey("riders.id"), nullable=True)
    assignment_status: Mapped[str] = mapped_column(String(50), default="UNASSIGNED", nullable=False)
    
    # Offer Timers (Section 11)
    offered_rider_id: Mapped[Optional[int]] = mapped_column(ForeignKey("riders.id"), nullable=True)
    assignment_offered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    rider: Mapped[Optional[Rider]] = relationship("Rider", foreign_keys=[rider_id])
    offered_rider: Mapped[Optional[Rider]] = relationship("Rider", foreign_keys=[offered_rider_id])
    batch: Mapped[Optional[Batch]] = relationship("Batch", back_populates="orders")
    items: Mapped[List[OrderItem]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="items")
    product: Mapped[Product] = relationship(lazy="selectin")