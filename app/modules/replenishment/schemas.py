from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional


# --- Request Schemas ---

class ReplenishmentCheckRequest(BaseModel):
    """Optional filters when triggering a replenishment check for a store."""
    product_ids: Optional[List[int]] = None  # If provided, only check these products


# --- Response Schemas ---

class ReplenishmentRecommendationResponse(BaseModel):
    """Single replenishment recommendation returned from the database."""
    id: int
    store_id: int
    product_id: int
    sku_id: str
    recommended_quantity: int
    confidence_score: float
    status: str
    purchase_order_id: Optional[int] = None
    ml_response_payload: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReplenishmentCheckResponse(BaseModel):
    """Response after triggering a replenishment check for a store."""
    store_id: int
    recommendations_generated: int
    recommendations: List[ReplenishmentRecommendationResponse]


class ReplenishmentConvertResponse(BaseModel):
    """Response after converting an approved recommendation into a Purchase Order."""
    recommendation: ReplenishmentRecommendationResponse
    purchase_order_id: int
    message: str = "Recommendation successfully converted to Purchase Order"
