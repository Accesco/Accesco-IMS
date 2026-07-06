"""
Request and response schemas for the Predictive Replenishment Engine API.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ReplenishmentRequest(BaseModel):
    """
    SKU-level inventory telemetry payload for replenishment prediction.

    Fields `available` and `reorder_level` are intentionally absent —
    they are direct arithmetic derivations of the target label and were
    excluded from training to prevent data leakage.
    """

    sku_id: str = Field(
        ...,
        description="Unique SKU identifier.",
        examples=["ACS-45566"],
    )
    store_id: Literal["DS-BLR-01", "DS-BLR-02", "DS-BLR-03"] = Field(
        ...,
        description="Dark store identifier. One of DS-BLR-01, DS-BLR-02, DS-BLR-03.",
        examples=["DS-BLR-01"],
    )
    on_hand: int = Field(
        ...,
        ge=0,
        description="Total physical units currently in the dark store.",
        examples=[1],
    )
    reserved: int = Field(
        ...,
        ge=0,
        description="Units held against pending customer orders.",
        examples=[0],
    )
    daily_velocity: float = Field(
        ...,
        gt=0,
        description="Average units sold per day (rolling average from order history).",
        examples=[10.0],
    )
    temp_zone: Literal["Ambient", "Chilled", "Frozen"] = Field(
        ...,
        description="Storage temperature zone for this SKU.",
        examples=["Ambient"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sku_id": "ACS-45566",
                    "store_id": "DS-BLR-01",
                    "on_hand": 1,
                    "reserved": 0,
                    "daily_velocity": 10.0,
                    "temp_zone": "Ambient",
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class ReplenishmentResponse(BaseModel):
    """
    Prediction result returned by the replenishment engine.
    """

    sku_id: str = Field(description="Echoed from request for traceability.")
    store_id: str = Field(description="Echoed from request for traceability.")
    urgent_reorder: bool = Field(
        description="True if the model predicts an urgent reorder is needed."
    )
    confidence_score: float = Field(
        description="Model's probability estimate for urgent reorder (0.0 – 1.0)."
    )
    action: str = Field(
        description=(
            "'GENERATE_PURCHASE_ORDER' when urgent_reorder is true, "
            "'NO_ACTION_REQUIRED' otherwise."
        )
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sku_id": "ACS-45566",
                    "store_id": "DS-BLR-01",
                    "urgent_reorder": True,
                    "confidence_score": 0.9928,
                    "action": "GENERATE_PURCHASE_ORDER",
                },
                {
                    "sku_id": "ACS-99682",
                    "store_id": "DS-BLR-01",
                    "urgent_reorder": False,
                    "confidence_score": 0.0312,
                    "action": "NO_ACTION_REQUIRED",
                },
            ]
        }
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = Field(description="Service status. Always 'ok' if the service is running.")
    model_features: List[str] = Field(description="Feature schema of the loaded model.")
