# tests/test_payment_webhook_security.py
"""
Security tests for Razorpay webhook signature verification and payment amount validation.
Tests cover:
  1. Valid webhook → payment confirmed
  2. Invalid signature → rejected
  3. Old mock bypass → rejected
  4. Amount tampering → rejected
  5. Non-existent order → safe exit
"""
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
import hmac
import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.store import Store
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.outbox import OutboxEvent
from app.modules.payments.service import PaymentService
from app.core.config import settings


def _compute_valid_signature(payload_bytes: bytes) -> str:
    """Helper: compute a valid HMAC-SHA256 signature for the given payload."""
    return hmac.new(
        key=settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()


def _build_webhook_payload(order_id: int, amount_paise: int) -> dict:
    """Helper: build a Razorpay-style webhook payload dict."""
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_123",
                    "order_id": f"order_mock_{order_id}",
                    "amount": amount_paise,
                    "currency": "INR",
                    "status": "captured"
                }
            }
        }
    }


@pytest_asyncio.fixture
async def setup_payment_test_data(db_session: AsyncSession):
    """Create a store, product, and a PENDING order with total_amount=100.00 (i.e. 10000 paise)."""
    store = Store(
        name="Payment Test Store", address="Addr", city="City",
        state="State", active=True, latitude=12.9716, longitude=77.5946
    )
    db_session.add(store)

    product = Product(sku="PAY-P1", name="Payment Product", category="C1", unit="pcs", active=True)
    db_session.add(product)
    await db_session.commit()

    order = Order(
        customer_id=1, store_id=store.id, status="PENDING",
        total_amount=100.00, payment_status="PENDING",
        latitude=12.9716, longitude=77.5946,
        sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(order)
    await db_session.commit()

    item = OrderItem(order_id=order.id, product_id=product.id, quantity=2, price=50.00)
    db_session.add(item)
    await db_session.commit()

    return store, product, order


# ─── Test 1: Valid Webhook ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_webhook_signature_and_amount(db_session: AsyncSession, setup_payment_test_data):
    """Valid signature + correct amount → payment confirmed, outbox event emitted."""
    _, _, order = setup_payment_test_data
    service = PaymentService(db_session)

    payload_dict = _build_webhook_payload(order.id, 10000)  # 100.00 INR in paise
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = _compute_valid_signature(payload_bytes)

    # Signature verification should pass
    assert service.verify_webhook_signature(payload_bytes, signature) is True

    # Handle webhook should create an outbox event
    await service.handle_webhook(payload_dict)

    result = await db_session.execute(
        select(OutboxEvent).where(OutboxEvent.event_type == "payments.confirmed")
    )
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.payload["order_id"] == order.id
    assert event.payload["amount"] == 100.00


# ─── Test 2: Invalid Signature ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_webhook_signature_rejected(db_session: AsyncSession, setup_payment_test_data):
    """Completely wrong signature → rejected, no outbox events."""
    _, _, order = setup_payment_test_data
    service = PaymentService(db_session)

    payload_dict = _build_webhook_payload(order.id, 10000)
    payload_bytes = json.dumps(payload_dict).encode("utf-8")

    # Use a bogus signature
    assert service.verify_webhook_signature(payload_bytes, "totally_invalid_signature") is False

    # Verify no outbox event was created (don't call handle_webhook since signature failed)
    result = await db_session.execute(
        select(OutboxEvent).where(OutboxEvent.event_type == "payments.confirmed")
    )
    assert result.scalar_one_or_none() is None


# ─── Test 3: Old Mock Bypass Rejected ────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_signature_bypass_rejected(db_session: AsyncSession, setup_payment_test_data):
    """The old 'mock_signature_bypass' value must no longer work."""
    _, _, order = setup_payment_test_data
    service = PaymentService(db_session)

    payload_dict = _build_webhook_payload(order.id, 10000)
    payload_bytes = json.dumps(payload_dict).encode("utf-8")

    # The previously-working bypass string must now be rejected
    assert service.verify_webhook_signature(payload_bytes, "mock_signature_bypass") is False


# ─── Test 4: Amount Tampering ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_amount_mismatch_rejected(db_session: AsyncSession, setup_payment_test_data):
    """
    Order total = ₹100.00 but webhook sends amount = ₹1 (100 paise).
    Payment must be rejected — no outbox event emitted.
    """
    _, _, order = setup_payment_test_data
    service = PaymentService(db_session)

    # Tampered amount: 100 paise = ₹1 instead of ₹100
    payload_dict = _build_webhook_payload(order.id, 100)
    await service.handle_webhook(payload_dict)

    # No payments.confirmed event should exist
    result = await db_session.execute(
        select(OutboxEvent).where(OutboxEvent.event_type == "payments.confirmed")
    )
    assert result.scalar_one_or_none() is None


# ─── Test 5: Non-existent Order ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nonexistent_order_safe_exit(db_session: AsyncSession, setup_payment_test_data):
    """
    Webhook references an order ID that doesn't exist in the database.
    Should log a warning and exit safely — no outbox events, no exceptions.
    """
    service = PaymentService(db_session)

    # Order ID 99999 does not exist
    payload_dict = _build_webhook_payload(99999, 10000)
    await service.handle_webhook(payload_dict)  # Should not raise

    # No outbox event should exist
    result = await db_session.execute(
        select(OutboxEvent).where(OutboxEvent.event_type == "payments.confirmed")
    )
    assert result.scalar_one_or_none() is None
