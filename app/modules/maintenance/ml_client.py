"""
Async HTTP client for communicating with the Maintenance Drift Engine.

The ML engine runs as a separate FastAPI service (see /maintenance-api)
and exposes:
    POST /predict-maintenance

Mirrors app/modules/eta/ml_client.py's pattern exactly.
"""
import logging

import httpx

from app.core.config import settings
from app.core.exceptions import MLServiceUnavailableException

logger = logging.getLogger(__name__)


def build_ml_payload(
    lane_id: str,
    terrain_factor: float,
    vehicle_age_years: float,
    km_since_last_service: float,
    days_since_last_service: int,
    avg_daily_km_this_interval: float,
    avg_load_utilization_pct: float,
    harsh_events_per_1000km: float,
) -> dict:
    return {
        "lane_id": lane_id,
        "terrain_factor": terrain_factor,
        "vehicle_age_years": vehicle_age_years,
        "km_since_last_service": km_since_last_service,
        "days_since_last_service": days_since_last_service,
        "avg_daily_km_this_interval": avg_daily_km_this_interval,
        "avg_load_utilization_pct": avg_load_utilization_pct,
        "harsh_events_per_1000km": harsh_events_per_1000km,
    }


async def call_ml_engine(payload: dict) -> dict:
    """
    Send a usage-snapshot payload to the Maintenance Drift Engine.
    Returns the parsed JSON response on success.
    Raises MLServiceUnavailableException on any connection or service error.
    """
    url = f"{settings.MAINTENANCE_ENGINE_URL}/predict-maintenance"
    timeout = getattr(settings, "MAINTENANCE_ENGINE_TIMEOUT", settings.TIMEOUT)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        logger.error("Maintenance Drift Engine timed out after %ds for lane %s", timeout, payload.get("lane_id"))
        raise MLServiceUnavailableException(
            "Maintenance Drift Engine request timed out. Please try again later."
        )
    except httpx.ConnectError:
        logger.error("Cannot connect to Maintenance Drift Engine at %s", url)
        raise MLServiceUnavailableException(
            "Cannot connect to Maintenance Drift Engine. Ensure the ML service is running."
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "Maintenance Drift Engine returned HTTP %d for lane %s: %s",
            e.response.status_code, payload.get("lane_id"), e.response.text
        )
        raise MLServiceUnavailableException(
            f"Maintenance Drift Engine returned an error (HTTP {e.response.status_code})."
        )
    except Exception as e:
        logger.exception("Unexpected error calling Maintenance Drift Engine: %s", str(e))
        raise MLServiceUnavailableException(
            "Unable to fetch maintenance prediction due to an unexpected error."
        )
