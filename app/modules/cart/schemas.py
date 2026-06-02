from pydantic import BaseModel
from typing import Dict

class CartItem(BaseModel):
    product_id: int
    quantity: int

class CartResponse(BaseModel):
    cart_id: str
    items: Dict[str, int]  # maps product_id (as string) to quantity
