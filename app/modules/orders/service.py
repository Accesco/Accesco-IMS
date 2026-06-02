from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreate
from app.models.order import Order
from app.core.exceptions import ResourceNotFoundException, IMSException
from app.core.events import create_outbox_event

class OrderService:
    def __init__(self, db: AsyncSession):
        self.repo = OrderRepository(db)

    async def get_order_by_id(self, order_id: int) -> Order:
        order = await self.repo.get_order_by_id(order_id)
        if not order:
            raise ResourceNotFoundException(f"Order with ID {order_id} not found")
        return order

    async def get_orders_by_customer(self, customer_id: int) -> List[Order]:
        return await self.repo.get_orders_by_customer(customer_id)

    async def place_order(self, order_data: OrderCreate, customer_id: int) -> Order:
        if not order_data.items:
            raise IMSException("Cannot place an order with empty items", 400)
            
        order = await self.repo.create_order(order_data, customer_id)
        
        # Prepare Kafka outbox event
        items_payload = [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": float(item.price)
            }
            for item in order.items
        ]
        
        await create_outbox_event(
            self.repo.db,
            "orders.placed",
            {
                "order_id": order.id,
                "customer_id": customer_id,
                "store_id": order_data.store_id,
                "total_amount": float(order.total_amount),
                "items": items_payload
            }
        )
        
        return order

    async def cancel_order(self, order_id: int) -> Order:
        order = await self.get_order_by_id(order_id)
        if order.status in ["CANCELLED", "COMPLETED"]:
            raise IMSException(f"Order cannot be cancelled in state: {order.status}", 400)
            
        await self.repo.update_order_status(order, "CANCELLED")
        await self.repo.update_order_payment(order, "REFUNDED") # Assume refund/cancelled logic
        
        # Emit orders.cancelled event
        await create_outbox_event(
            self.repo.db,
            "orders.cancelled",
            {
                "order_id": order.id,
                "customer_id": order.customer_id
            }
        )
        
        return order

    async def confirm_order_payment(self, order_id: int) -> Order:
        order = await self.get_order_by_id(order_id)
        await self.repo.update_order_status(order, "CONFIRMED")
        await self.repo.update_order_payment(order, "COMPLETED")
        return order
