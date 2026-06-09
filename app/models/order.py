from typing import List, Optional

from sqlalchemy import String, Numeric, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.product import Product
from app.models.rider import Rider


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    store_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False
    )

    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    payment_status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False
    )

    rider_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("riders.id"),
        nullable=True
    )

    assignment_status: Mapped[str] = mapped_column(
        String(50),
        default="UNASSIGNED",
        nullable=False
    )

    rider: Mapped["Rider"] = relationship("Rider")

    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items"
    )

    product: Mapped[Product] = relationship(
        lazy="selectin"
    )