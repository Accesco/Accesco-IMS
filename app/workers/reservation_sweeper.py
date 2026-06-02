import asyncio
import logging
import sys
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.modules.inventory.service import InventoryService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("reservation_sweeper")

async def sweep_expired_reservations() -> int:
    """
    Finds and releases all expired inventory reservations.
    Returns the number of reservations released.
    """
    async with async_session_maker() as db:
        try:
            service = InventoryService(db)
            released_count = await service.release_expired_reservations()
            if released_count > 0:
                await db.commit()
                logger.info(f"Successfully released {released_count} expired reservations")
            return released_count
        except Exception as e:
            logger.error(f"Error sweeping expired reservations: {e}")
            await db.rollback()
            return 0

async def main() -> None:
    logger.info("Starting Reservation Expiry Sweeper worker")
    
    try:
        while True:
            released = await sweep_expired_reservations()
            # Run sweep every 10 seconds
            await asyncio.sleep(10.0)
    except asyncio.CancelledError:
        logger.info("Sweeper worker cancel requested")

if __name__ == "__main__":
    asyncio.run(main())
