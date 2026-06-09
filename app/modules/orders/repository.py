from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.order import Order, OrderItem
from app.modules.orders.schemas import OrderCreate
from sqlalchemy.orm import selectinload

class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def get_orders_by_customer(self, customer_id: int) -> List[Order]:
        result = await self.db.execute(select(Order).where(Order.customer_id == customer_id))
        return list(result.scalars().all())

    async def create_order(self, order_data: OrderCreate, customer_id: int) -> Order:
        # Calculate total amount
        total = sum(item.price * item.quantity for item in order_data.items)
        
        db_order = Order(
            customer_id=customer_id,
            store_id=order_data.store_id,
            status="PENDING",
            total_amount=total,
            payment_status="PENDING"
        )
        self.db.add(db_order)
        await self.db.flush()  # get order ID

        for item in order_data.items:
            db_item = OrderItem(
                order_id=db_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            )
            self.db.add(db_item)
            
        await self.db.flush()

        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == db_order.id)
        )

        return result.scalar_one()

    async def update_order_status(self, order: Order, status: str) -> Order:
        order.status = status
        await self.db.flush()
        return order

    async def update_order_payment(self, order: Order, payment_status: str) -> Order:
        order.payment_status = payment_status
        await self.db.flush()
        return order
class OrderItemRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
