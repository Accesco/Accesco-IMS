"""
Async HTTP client for communicating with the Predictive Replenishment ML Engine.

The ML engine runs as a separate FastAPI service and exposes:
    POST /api/v1/inventory/check

This client transforms IMS inventory data into the ML engine's expected
telemetry format and handles connection failures gracefully.
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import MLServiceUnavailableException

logger = logging.getLogger(__name__)

# Store name → one-hot mapping for Dark_Store_ID features
# Extend this mapping as new Bangalore dark stores are added
DARK_STORE_MAPPING = {
    "DS_BLR_01": "Dark_Store_ID_DS_BLR_01",
    "DS_BLR_02": "Dark_Store_ID_DS_BLR_02",
    "DS_BLR_03": "Dark_Store_ID_DS_BLR_03",
}

# Product category → one-hot mapping for Temp_Zone features
TEMP_ZONE_MAPPING = {
    "Ambient": "Temp_Zone_Ambient",
    "Chilled": "Temp_Zone_Chilled",
    "Frozen": "Temp_Zone_Frozen",
}

# Default daily velocity when actual sales data is not available
DEFAULT_DAILY_VELOCITY = 5.0

# Default reorder quantity when ML engine does not specify one
DEFAULT_REORDER_QUANTITY = 25


def build_ml_payload(
    sku_id: str,
    on_hand: int,
    reserved: int,
    daily_velocity: float = DEFAULT_DAILY_VELOCITY,
    store_name: Optional[str] = None,
    temp_zone: Optional[str] = None,
) -> dict:
    """
    Transform IMS inventory data into the ML engine's expected telemetry format.

    The ML engine expects one-hot encoded features for Dark_Store_ID and Temp_Zone.
    """
    payload = {
        "sku_id": sku_id,
        "On_Hand": on_hand,
        "Reserved": reserved,
        "Daily_Velocity": daily_velocity,
    }

    # One-hot encode dark store ID
    for store_key, feature_name in DARK_STORE_MAPPING.items():
        payload[feature_name] = 1 if store_name and store_key in store_name else 0

    # One-hot encode temperature zone
    for zone_key, feature_name in TEMP_ZONE_MAPPING.items():
        payload[feature_name] = 1 if temp_zone and zone_key.lower() == temp_zone.lower() else 0

    # If no temp zone matched, default to Ambient
    if not any(payload.get(v, 0) for v in TEMP_ZONE_MAPPING.values()):
        payload["Temp_Zone_Ambient"] = 1

    return payload


async def call_ml_engine(payload: dict) -> dict:
    """
    Send a SKU telemetry payload to the ML Replenishment Engine.

    Returns the parsed JSON response on success.
    Raises MLServiceUnavailableException on any connection or service error.
    """
    url = f"{settings.REPLENISHMENT_ENGINE_URL}/api/v1/inventory/check"
    timeout = settings.REPLENISHMENT_ENGINE_TIMEOUT

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        logger.error("ML Replenishment Engine timed out after %ds for SKU %s", timeout, payload.get("sku_id"))
        raise MLServiceUnavailableException(
            "Replenishment Engine request timed out. Please try again later."
        )
    except httpx.ConnectError:
        logger.error("Cannot connect to ML Replenishment Engine at %s", url)
        raise MLServiceUnavailableException(
            "Cannot connect to Replenishment Engine. Ensure the ML service is running."
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "ML Replenishment Engine returned HTTP %d for SKU %s: %s",
            e.response.status_code, payload.get("sku_id"), e.response.text
        )
        raise MLServiceUnavailableException(
            f"Replenishment Engine returned an error (HTTP {e.response.status_code})."
        )
    except Exception as e:
        logger.exception("Unexpected error calling ML Replenishment Engine: %s", str(e))
        raise MLServiceUnavailableException(
            "Unable to fetch replenishment recommendations due to an unexpected error."
        )
