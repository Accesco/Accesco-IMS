import logging
from typing import Any, Dict

from app.modules.dashboard.events import (
    OrderCreatedEvent,
    OrderUpdatedEvent,
    PaymentConfirmedEvent,
    InventoryUpdatedEvent,
    InventoryLowEvent,
    ShipmentDeliveredEvent,
    OrderCancelledEvent,
)
from app.modules.dashboard.cache import DashboardCacheManager
from app.modules.dashboard.notifier import DashboardNotifier

logger = logging.getLogger("dashboard.consumer")


class DashboardEventHandler:
    """
    Handles Kafka events relevant to the dashboard.

    Responsibilities:
    - Deserialize raw payloads into typed event models.
    - Invalidate only the cache keys affected by each event.
    - Broadcast push notifications to connected WebSocket clients.
    - Never crash the parent consumer on individual event failure.
    """

    def __init__(self, cache_manager: DashboardCacheManager, notifier: DashboardNotifier):
        self.cache_manager = cache_manager
        self.notifier = notifier

    async def handle(self, topic: str, payload: Dict[str, Any]) -> None:
        try:
            if topic == "orders.created":
                await self._on_order_created(payload)
            elif topic == "orders.updated":
                await self._on_order_updated(payload)
            elif topic == "payments.confirmed":
                await self._on_payment_confirmed(payload)
            elif topic == "inventory.updated":
                await self._on_inventory_updated(payload)
            elif topic == "inventory.low":
                await self._on_inventory_low(payload)
            elif topic == "shipments.delivered":
                await self._on_shipment_delivered(payload)
            elif topic == "orders.cancelled":
                await self._on_order_cancelled(payload)
            else:
                logger.debug(f"Dashboard handler: no action defined for topic '{topic}'")
        except Exception as e:
            # Failures here must NEVER crash the parent consumer loop
            logger.error(
                f"Dashboard event handler failed for topic '{topic}': {e}",
                exc_info=True
            )

    # ── handlers ──────────────────────────────────────────────────────────────

    async def _on_order_created(self, payload: Dict[str, Any]) -> None:
        event = OrderCreatedEvent(**payload)
        logger.info(f"order.created received: order_id={event.order_id}")

        await self.cache_manager.invalidate_summary()
        await self.cache_manager.invalidate_charts()         # revenue + orders charts
        await self.notifier.notify_order_created(event.order_id)

    async def _on_order_updated(self, payload: Dict[str, Any]) -> None:
        event = OrderUpdatedEvent(**payload)
        logger.info(f"order.updated received: order_id={event.order_id} status={event.status}")

        await self.cache_manager.invalidate_summary()
        await self.cache_manager.invalidate_charts()
        await self.notifier.notify_order_updated(event.order_id, event.status)

    async def _on_payment_confirmed(self, payload: Dict[str, Any]) -> None:
        event = PaymentConfirmedEvent(**payload)
        logger.info(f"payment.confirmed received: order_id={event.order_id}")

        # A confirmed payment affects revenue and order counts
        await self.cache_manager.invalidate_summary()
        await self.cache_manager.invalidate_charts()

    async def _on_inventory_updated(self, payload: Dict[str, Any]) -> None:
        event = InventoryUpdatedEvent(**payload)
        logger.info(
            f"inventory.updated received: product_id={event.product_id} "
            f"available={event.available_quantity}"
        )

        await self.cache_manager.invalidate_inventory()
        await self.cache_manager.invalidate_summary()
        await self.notifier.notify_inventory_updated(event.product_id, event.available_quantity)

    async def _on_inventory_low(self, payload: Dict[str, Any]) -> None:
        event = InventoryLowEvent(**payload)
        logger.info(
            f"inventory.low received: product_id={event.product_id} "
            f"available={event.available_quantity}"
        )

        await self.cache_manager.invalidate_inventory()
        await self.notifier.notify_new_alert(
            alert_id=event.product_id,
            message=f"Low stock for product {event.product_id}: {event.available_quantity} units remaining"
        )

    async def _on_shipment_delivered(self, payload: Dict[str, Any]) -> None:
        event = ShipmentDeliveredEvent(**payload)
        logger.info(f"shipment.delivered received: order_id={event.order_id}")

        # Delivery affects SLA and overall summary
        await self.cache_manager.invalidate_summary()
        await self.cache_manager.invalidate_charts()
        await self.notifier.notify_order_updated(event.order_id, "DELIVERED")

    async def _on_order_cancelled(self, payload: Dict[str, Any]) -> None:
        event = OrderCancelledEvent(**payload)
        logger.info(f"order.cancelled received: order_id={event.order_id}")

        await self.cache_manager.invalidate_summary()
        await self.cache_manager.invalidate_charts()
        await self.notifier.notify_order_updated(event.order_id, "CANCELLED")
