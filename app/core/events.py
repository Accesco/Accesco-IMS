from sqlalchemy.ext.asyncio import AsyncSession
import json

async def create_outbox_event(session: AsyncSession, event_type: str, payload: dict) -> None:
    """
    Creates an OutboxEvent record in the database within the current transaction.
    This guarantees that the event is committed if and only if the transaction succeeds.
    """
    # Import locally to prevent circular dependency issues
    from app.models.outbox import OutboxEvent
    
    event = OutboxEvent(
        event_type=event_type,
        payload=payload,
        status="PENDING"
    )
    session.add(event)
