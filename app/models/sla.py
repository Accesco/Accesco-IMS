
from __future__ import annotations

from datetime import datetime
from razorpay import Order
from sqlalchemy import String, Integer, ForeignKey, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SLAAlert(Base, TimestampMixin):
    __tablename__ = "sla_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Alert levels: RISK, BREACH, CRITICAL_BREACH
    alert_level: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Calculated delay parameters
    picking_delay_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    assignment_delay_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    delivery_delay_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    eta_drift_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True) # ACTIVE, ACKNOWLEDGED, RESOLVED
    escalation_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship("Order", lazy="selectin")