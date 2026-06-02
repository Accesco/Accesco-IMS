from pydantic import BaseModel
from typing import Dict, Any

class CheckoutSessionCreate(BaseModel):
    order_id: int

class CheckoutSessionResponse(BaseModel):
    razorpay_order_id: str
    amount: float
    currency: str
    status: str

class RazorpayWebhook(BaseModel):
    event: str
    payload: Dict[str, Any]
