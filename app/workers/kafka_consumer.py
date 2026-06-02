import asyncio
import json
import logging
import sys
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.modules.orders.service import OrderService
from app.modules.inventory.service import InventoryService
from app.modules.inventory.schemas import InventoryReservationCreate
from app.modules.procurement.service import ProcurementService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("kafka_consumer_worker")

async def process_message(topic: str, payload: dict) -> None:
    logger.info(f"Processing event from topic '{topic}': {payload}")
    
    async with async_session_maker() as db:
        try:
            if topic == "payments.confirmed":
                order_id = payload.get("order_id")
                if not order_id:
                    logger.error("Missing order_id in payments.confirmed payload")
                    return
                
                # 1. Confirm order payment and status
                order_service = OrderService(db)
                order = await order_service.confirm_order_payment(order_id)
                logger.info(f"Confirmed Order ID {order_id} in database")

                # 2. Create inventory reservations for each item in the order
                inventory_service = InventoryService(db)
                for item in order.items:
                    res_data = InventoryReservationCreate(
                        store_id=order.store_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        order_id=str(order.id),
                        expires_in_seconds=600  # 10 minutes reservation
                    )
                    reservation = await inventory_service.reserve_stock(res_data)
                    logger.info(
                        f"Created stock reservation {reservation.id} for product {item.product_id} "
                        f"in store {order.store_id} (quantity: {item.quantity})"
                    )
                
                await db.commit()
                logger.info(f"Successfully processed payments.confirmed for Order ID {order_id}")

            elif topic == "inventory.low":
                product_id = payload.get("product_id")
                available_quantity = payload.get("available_quantity")
                if not product_id:
                    logger.error("Missing product_id in inventory.low payload")
                    return
                
                logger.info(f"Inventory low alert for product {product_id}. Available: {available_quantity}")
                
                # Automatically generate draft purchase order
                procurement_service = ProcurementService(db)
                # Order a standard reorder amount, say 100 units
                po = await procurement_service.auto_generate_draft_po(product_id=product_id, quantity=100)
                logger.info(f"Automatically generated draft Purchase Order {po.id} for product {product_id}")
                
                await db.commit()

            elif topic == "orders.cancelled":
                order_id = payload.get("order_id")
                if not order_id:
                    logger.error("Missing order_id in orders.cancelled payload")
                    return
                
                # Find all pending reservations for this order and release them
                inventory_service = InventoryService(db)
                reservations = await inventory_service.get_reservations_by_order(str(order_id))
                
                logger.info(f"Releasing reservations for cancelled Order ID {order_id}. Found {len(reservations)} reservations.")
                released_count = 0
                for res in reservations:
                    if res.status == "PENDING":
                        await inventory_service.release_reservation(res.id, status="CANCELLED")
                        released_count += 1
                        
                await db.commit()
                logger.info(f"Released {released_count} reservations for Order ID {order_id}")

            else:
                logger.warning(f"Unrecognized topic: {topic}")
                
        except Exception as e:
            logger.error(f"Error processing message from topic '{topic}': {e}", exc_info=True)
            await db.rollback()

async def main() -> None:
    topics = ["payments.confirmed", "inventory.low", "orders.cancelled"]
    logger.info(f"Subscribing to Kafka topics: {topics}")
    
    # Retry loop to connect to Kafka (handles broker starting up delayed)
    consumer = None
    for attempt in range(1, 11):
        try:
            consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id="ims_consumer_group",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest"
            )
            await consumer.start()
            logger.info("Kafka consumer connected and started successfully")
            break
        except Exception as e:
            logger.warning(f"Kafka connection attempt {attempt} failed: {e}. Retrying in 3 seconds...")
            await asyncio.sleep(3)
            
    if not consumer:
        logger.error("Could not establish connection to Kafka. Exiting.")
        sys.exit(1)

    try:
        async for msg in consumer:
            try:
                await process_message(msg.topic, msg.value)
            except Exception as e:
                logger.error(f"Exception during msg consumption loops: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(main())
