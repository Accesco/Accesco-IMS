from . import repository
from app.core.exceptions import ResourceNotFoundException, IMSException

async def assign_order(db, order_id):
    order = await repository.get_order_for_update(db, order_id)

    if not order:
        raise ResourceNotFoundException("Order not found")

    if order.status in ["CANCELLED", "COMPLETED"]:
        raise IMSException(f"Cannot assign rider to order in state: {order.status}", 400)

    if order.rider_id or order.assignment_status == "ASSIGNED":
        raise IMSException("Order already assigned", 400)

    selected_rider = await repository.get_available_rider_for_update(db)

    if not selected_rider:
        raise IMSException("No available riders", 400)

    await repository.assign_rider_to_order(
        db,
        order,
        selected_rider
    )

    return {
        "order_id": order.id,
        "rider_id": selected_rider.id,
        "status": "ASSIGNED"
    }