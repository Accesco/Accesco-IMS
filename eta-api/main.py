"""
ETA Drift Engine — FastAPI Inference Service
Accesco Living | TMS

Endpoint:  POST /predict-eta
Model:     GradientBoostingRegressor pipeline (eta_drift_model.joblib)

Predicts the "drift" between a naive ETA (distance remaining / current
speed) and the actual remaining time, using signals available at
telemetry-ping time: lane, carrier, time of day, current/average speed.
See eta-engine/ for the training code and methodology.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from schemas import ETARequest, ETAResponse, HealthResponse
from inference import ETAInferenceService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model loaded ONCE at startup via lifespan context — not per request
# ---------------------------------------------------------------------------
inference_service: ETAInferenceService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global inference_service
    model_path = os.getenv("MODEL_PATH", "eta_drift_model.joblib")
    logger.info(f"Loading model from '{model_path}' ...")
    inference_service = ETAInferenceService(model_path)
    logger.info(f"Model ready. Features: {inference_service.expected_features}")
    yield
    logger.info("Shutting down inference service.")


app = FastAPI(
    title="ETA Drift Engine",
    description=(
        "REST API for the Accesco Living TMS ETA prediction model. "
        "Accepts a single telemetry snapshot (lane, carrier, current speed, "
        "distance remaining, time of day) and returns a naive ETA, the "
        "model's predicted drift correction, and the corrected ETA."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Returns service status and the model feature schema currently loaded.
    Use this to verify the service is running and the correct model is loaded.
    """
    return HealthResponse(
        status="ok",
        model_features=inference_service.expected_features,
    )


@app.post(
    "/predict-eta",
    response_model=ETAResponse,
    tags=["Prediction"],
    summary="Predict corrected ETA for an in-transit shipment",
    responses={
        200: {"description": "Prediction returned successfully."},
        422: {"description": "Validation error — check request schema."},
        500: {"description": "Internal inference error."},
    },
)
def predict_eta(request: ETARequest):
    """
    Runs the ETA drift model on the submitted telemetry snapshot.

    **Returns:**
    - `naive_eta_remaining_min` — distance_remaining_km / current_speed_kmh, in minutes
    - `predicted_drift_min` — model's correction (can be negative or positive)
    - `corrected_eta_remaining_min` — naive + predicted_drift, the number to actually display

    **Feature notes:**
    - `current_speed_kmh=0` (a stopped truck) is handled safely, not a 422/500.
    - `lane_id` / `carrier_id` are accepted as plain strings and one-hot
      encoded internally before hitting the model.
    """
    result = inference_service.predict(request)
    return result
