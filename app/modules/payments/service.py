import hmac
import hashlib
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import razorpay

from app.core.config import settings
from app.core.exceptions import IMSException, PaymentVerificationFailedException
from app.core.events import create_outbox_event
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.schemas import CheckoutSessionCreate

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db: AsyncSession):
        self.repo = PaymentRepository(db)
        # Initialize Razorpay client. If mock keys, use mock behavior.
        try:
            self.razorpay_client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        except Exception:
            self.razorpay_client = None

    async def create_checkout_session(self, session_data: CheckoutSessionCreate) -> Dict[str, Any]:
        order = await self.repo.get_order(session_data.order_id)
        if not order:
            raise IMSException(f"Order with ID {session_data.order_id} not found", 404)
        
        if order.status != "PENDING":
            raise IMSException(f"Order with ID {session_data.order_id} is already in status: {order.status}", 400)

        amount_in_paise = int(order.total_amount * 100)
        
        # Simulate or hit Razorpay API
        if settings.RAZORPAY_KEY_ID.startswith("rzp_test_mock") or not self.razorpay_client:
            # Return mocked Razorpay response
            mock_razorpay_order_id = f"order_mock_{order.id}"
            return {
                "razorpay_order_id": mock_razorpay_order_id,
                "amount": float(order.total_amount),
                "currency": "INR",
                "status": "created"
            }
        
        try:
            params = {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": f"receipt_order_{order.id}",
                "payment_capture": 1
            }
            razorpay_order = self.razorpay_client.order.create(data=params)
            return {
                "razorpay_order_id": razorpay_order["id"],
                "amount": float(order.total_amount),
                "currency": "INR",
                "status": razorpay_order["status"]
            }
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {e}")
            raise IMSException(f"Razorpay integration error: {str(e)}", 502)

    def verify_webhook_signature(self, payload_body: bytes, signature: str) -> bool:
        """
        Verifies Razorpay Webhook signature using HMAC-SHA256.
        """
        if settings.RAZORPAY_WEBHOOK_SECRET == "mockwebhooksecret789":
            # For local mock testing, bypass signature check if specific test header is provided
            if signature == "mock_signature_bypass":
                return True

        try:
            # In python, we can verify manually:
            expected_signature = hmac.new(
                key=settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
                msg=payload_body,
                digestmod=hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Webhook signature calculation error: {e}")
            return False

    async def handle_webhook(self, event_data: dict) -> None:
        """
        Processes Razorpay Webhook payload.
        Emits payments.confirmed Kafka event if payment is captured/confirmed.
        """
        event_type = event_data.get("event")
        
        if event_type == "payment.captured":
            payload_entity = event_data.get("payload", {}).get("payment", {}).get("entity", {})
            razorpay_order_id = payload_entity.get("order_id")
            razorpay_payment_id = payload_entity.get("id")
            amount = payload_entity.get("amount", 0) / 100.0

            # Find matching order.
            # In mock setups, razorpay_order_id is 'order_mock_<id>'
            order_id = None
            if razorpay_order_id:
                if razorpay_order_id.startswith("order_mock_"):
                    try:
                        order_id = int(razorpay_order_id.replace("order_mock_", ""))
                    except ValueError:
                        pass
                else:
                    # Parse from receipt or try integer directly
                    receipt = payload_entity.get("receipt", "")
                    if receipt.startswith("receipt_order_"):
                        try:
                            order_id = int(receipt.replace("receipt_order_", ""))
                        except ValueError:
                            pass
            
            if not order_id:
                # Fallback: check if we can query orders or parse order_id from notes/payload
                notes = payload_entity.get("notes", {})
                order_id_note = notes.get("order_id")
                if order_id_note:
                    order_id = int(order_id_note)

            if not order_id:
                logger.warning("Could not associate Razorpay webhook with any IMS Order ID")
                return

            logger.info(f"Payment captured for Order ID {order_id}. Emitting payments.confirmed event.")

            # Create outbox event payments.confirmed
            await create_outbox_event(
                self.repo.db,
                "payments.confirmed",
                {
                    "order_id": order_id,
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "amount": amount
                }
            )
        else:
            logger.info(f"Ignored payment webhook event type: {event_type}")
            return
