import asyncio
import logging
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.kafka import kafka_producer
from app.models.outbox import OutboxEvent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("outbox_processor")

async def process_outbox_events() -> int:
    """
    Queries pending outbox events, publishes them to Kafka, and marks them as PROCESSED.
    Returns the number of processed events.
    """
    async with async_session_maker() as db:
        try:
            # Query pending events ordered by creation time
            result = await db.execute(
                select(OutboxEvent)
                .where(OutboxEvent.status == "PENDING")
                .order_by(OutboxEvent.created_at.asc())
                .limit(50)
                .with_for_update(skip_locked=True)  # concurrency safe!
            )
            events = result.scalars().all()
            
            if not events:
                return 0
                
            logger.info(f"Found {len(events)} pending outbox events to process")
            processed_count = 0
            
            for event in events:
                try:
                    logger.info(f"Publishing event {event.id} ({event.event_type}) to Kafka")
                    # Publish to Kafka
                    # We use event_type as the Kafka topic
                    await kafka_producer.send_event(
                        topic=event.event_type,
                        key=str(event.id),
                        value=event.payload
                    )
                    
                    event.status = "PROCESSED"
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to publish event {event.id} to Kafka: {e}")
                    event.status = "FAILED"
                    # We still commit the status update so we don't get stuck in an infinite loop on a bad event,
                    # or we can retry. For simplicity, marking as FAILED allows operators to review.
            
            await db.commit()
            return processed_count
            
        except Exception as e:
            logger.error(f"Error querying outbox events: {e}")
            await db.rollback()
            return 0

async def main() -> None:
    logger.info("Starting Outbox Event Processor worker")
    
    # Start Kafka producer client
    try:
        await kafka_producer.start()
    except Exception as e:
        logger.error(f"Failed to start Kafka producer in outbox worker: {e}. Exiting.")
        sys.exit(1)
        
    try:
        while True:
            processed = await process_outbox_events()
            if processed > 0:
                logger.info(f"Processed {processed} outbox events")
                # If we processed events, loop immediately in case there are more
                await asyncio.sleep(0.1)
            else:
                # Idle poll sleep
                await asyncio.sleep(2.0)
    except asyncio.CancelledError:
        logger.info("Outbox worker cancel requested")
    finally:
        await kafka_producer.stop()

if __name__ == "__main__":
    asyncio.run(main())
