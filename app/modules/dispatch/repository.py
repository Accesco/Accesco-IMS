from sqlalchemy import select

from app.models.order import Order
from app.models.rider import Rider


async def get_order_by_id(db, order_id: int):
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_available_riders(db):
    result = await db.execute(
        select(Rider).where(
            Rider.is_available == True
        )
    )
    return result.scalars().all()


async def assign_rider_to_order(
    db,
    order: Order,
    rider: Rider
):
    order.rider_id = rider.id
    order.assignment_status = "ASSIGNED"

    rider.is_available = False
    rider.status = "ASSIGNED"

    await db.commit()
    await db.refresh(order)

    return order