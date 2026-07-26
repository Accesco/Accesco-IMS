from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

class PickWave(Base, TimestampMixin):
    __tablename__ = "pick_waves"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False) # PENDING, IN_PROGRESS, COMPLETED

    # Relationships
    tasks: Mapped[List["PickTask"]] = relationship(
        "PickTask", back_populates="wave", cascade="all, delete-orphan", lazy="selectin"
    )


class PickTask(Base, TimestampMixin):
    __tablename__ = "pick_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    wave_id: Mapped[int] = mapped_column(ForeignKey("pick_waves.id", ondelete="CASCADE"), index=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    assigned_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False) # PENDING, IN_PROGRESS, COMPLETED, CANCELLED

    # Relationships
    wave: Mapped["PickWave"] = relationship("PickWave", back_populates="tasks")
    items: Mapped[List["PickTaskItem"]] = relationship(
        "PickTaskItem", back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )


class PickTaskItem(Base):
    __tablename__ = "pick_task_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pick_task_id: Mapped[int] = mapped_column(ForeignKey("pick_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)
    expected_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    picked_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    task: Mapped["PickTask"] = relationship("PickTask", back_populates="items")
