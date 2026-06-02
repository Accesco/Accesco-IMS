from fastapi import APIRouter, Depends, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.database import get_db
from app.modules.auth.routes import get_current_user
from app.core.exceptions import PaymentVerificationFailedException
from app.modules.payments.schemas import CheckoutSessionCreate, CheckoutSessionResponse
from app.modules.payments.service import PaymentService

router = APIRouter(tags=["payments"])


@router.post("/payments/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    session_data: CheckoutSessionCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user)
):
    service = PaymentService(db)
    return await service.create_checkout_session(session_data)


@router.post("/webhooks/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    body = await request.body()
    service = PaymentService(db)
    
    # Verify signature
    if not x_razorpay_signature:
        raise PaymentVerificationFailedException("Missing Razorpay signature header")
        
    is_valid = service.verify_webhook_signature(body, x_razorpay_signature)
    if not is_valid:
        raise PaymentVerificationFailedException("Invalid signature")
        
    # Process event
    try:
        event_data = json.loads(body.decode("utf-8"))
    except Exception:
        raise PaymentVerificationFailedException("Invalid JSON payload")
        
    await service.handle_webhook(event_data)
    return {"status": "ok"}
