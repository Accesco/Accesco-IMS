from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Notification classification
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., INVENTORY_LOW, ORDER_STATUS, SYSTEM, WAREHOUSE, TRANSFER
    priority: Mapped[str] = mapped_column(
        String(20), default="NORMAL", nullable=False, index=True
    )  # LOW, NORMAL, HIGH, CRITICAL

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Read state
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Optional reference to a related entity for deep linking
    reference_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "order", "inventory_item", "purchase_order", "warehouse"
    reference_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )  # Entity ID (string to support composite keys)

    # Flexible metadata for frontend rendering
    metadata_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    user = relationship("User", lazy="selectin")
