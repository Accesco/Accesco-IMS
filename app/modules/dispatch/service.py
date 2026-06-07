from . import repository


async def assign_order(db, order_id):
    order = await repository.get_order_by_id(db, order_id)

    if not order:
        raise ValueError("Order not found")

    if order.rider_id:
        raise ValueError("Order already assigned")

    available_riders = await repository.get_available_riders(db)

    if not available_riders:
        raise ValueError("No available riders")

    selected_rider = available_riders[0]

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