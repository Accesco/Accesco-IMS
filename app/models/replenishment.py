from typing import Optional
from sqlalchemy import String, Float, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.models.store import Store
from app.models.product import Product


class ReplenishmentRecommendation(Base, TimestampMixin):
    __tablename__ = "replenishment_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String(50), nullable=False)
    recommended_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False, index=True)  # PENDING, APPROVED, REJECTED, CONVERTED
    purchase_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    ml_response_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    store: Mapped[Store] = relationship(lazy="selectin")
    product: Mapped[Product] = relationship(lazy="selectin")
    purchase_order = relationship("PurchaseOrder", lazy="selectin")
