"""
Async HTTP client for communicating with the ETA Drift Engine.

The ML engine runs as a separate FastAPI service (see /eta-api) and
exposes:
    POST /predict-eta

This client passes through a telemetry snapshot and handles connection
failures gracefully, matching the replenishment module's ml_client.py
pattern.
"""
import logging

import httpx

from app.core.config import settings
from app.core.exceptions import MLServiceUnavailableException

logger = logging.getLogger(__name__)


def build_ml_payload(
    lane_id: str,
    carrier_id: str,
    carrier_on_time_score: float,
    hour_of_day: float,
    is_rush_hour: bool,
    distance_remaining_km: float,
    progress_fraction: float,
    current_speed_kmh: float,
    avg_speed_so_far_kmh: float,
) -> dict:
    """Build the telemetry payload the ETA Drift Engine expects. Kept
    as its own function (even though it's currently a straight
    passthrough) so a future re-mapping of IMS-side fields to the
    model's feature names has one place to change, matching the
    replenishment module's build_ml_payload() pattern."""
    return {
        "lane_id": lane_id,
        "carrier_id": carrier_id,
        "carrier_on_time_score": carrier_on_time_score,
        "hour_of_day": hour_of_day,
        "is_rush_hour": is_rush_hour,
        "distance_remaining_km": distance_remaining_km,
        "progress_fraction": progress_fraction,
        "current_speed_kmh": current_speed_kmh,
        "avg_speed_so_far_kmh": avg_speed_so_far_kmh,
    }


async def call_ml_engine(payload: dict) -> dict:
    """
    Send a telemetry payload to the ETA Drift Engine.

    Returns the parsed JSON response on success.
    Raises MLServiceUnavailableException on any connection or service error.
    """
    url = f"{settings.ETA_ENGINE_URL}/predict-eta"
    timeout = settings.ETA_ENGINE_TIMEOUT

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        logger.error("ETA Drift Engine timed out after %ds for lane %s", timeout, payload.get("lane_id"))
        raise MLServiceUnavailableException(
            "ETA Drift Engine request timed out. Please try again later."
        )
    except httpx.ConnectError:
        logger.error("Cannot connect to ETA Drift Engine at %s", url)
        raise MLServiceUnavailableException(
            "Cannot connect to ETA Drift Engine. Ensure the ML service is running."
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "ETA Drift Engine returned HTTP %d for lane %s: %s",
            e.response.status_code, payload.get("lane_id"), e.response.text
        )
        raise MLServiceUnavailableException(
            f"ETA Drift Engine returned an error (HTTP {e.response.status_code})."
        )
    except Exception as e:
        logger.exception("Unexpected error calling ETA Drift Engine: %s", str(e))
        raise MLServiceUnavailableException(
            "Unable to fetch ETA prediction due to an unexpected error."
        )
