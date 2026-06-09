from sqlalchemy import select

from app.models.order import Order
from app.models.rider import Rider


async def get_order_for_update(db, order_id: int):
    result = await db.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def get_available_rider_for_update(db):
    result = await db.execute(
        select(Rider).where(
            Rider.is_available == True
        ).limit(1).with_for_update(skip_locked=True)
    )
    return result.scalar_one_or_none()


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