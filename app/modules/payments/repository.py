from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import select
from app.models.order import Order

class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_order(self, order_id: int) -> Optional[Order]:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def update_order_payment_status(self, order_id: int, payment_status: str, order_status: str) -> Optional[Order]:
        order = await self.get_order(order_id)
        if order:
            order.payment_status = payment_status
            order.status = order_status
            await self.db.flush()
        return order
