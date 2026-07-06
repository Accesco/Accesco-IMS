"""
Predictive Replenishment Engine — FastAPI Inference Service
Accesco Living | Author: Jai Jain (ML Intern)

Endpoint:  POST /predict-replenishment
Model:     XGBoost binary classifier (predictive_replenishment_model.pkl)
"""

import os
import logging
from contextlib import asynccontextmanager

import joblib
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from schemas import ReplenishmentRequest, ReplenishmentResponse, HealthResponse
from inference import ReplenishmentInferenceService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model loaded ONCE at startup via lifespan context — not per request
# ---------------------------------------------------------------------------
inference_service: ReplenishmentInferenceService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global inference_service
    model_path = os.getenv("MODEL_PATH", "predictive_replenishment_model.pkl")
    logger.info(f"Loading model from '{model_path}' ...")
    inference_service = ReplenishmentInferenceService(model_path)
    logger.info(f"Model ready. Features: {inference_service.expected_features}")
    yield
    logger.info("Shutting down inference service.")


app = FastAPI(
    title="Predictive Replenishment Engine",
    description=(
        "REST API for the Accesco Living dark store inventory replenishment model. "
        "Accepts SKU-level inventory telemetry and returns an urgent reorder prediction "
        "with a confidence score."
    ),
    version="0.3.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
    "/predict-replenishment",
    response_model=ReplenishmentResponse,
    tags=["Prediction"],
    summary="Predict urgent reorder for a SKU",
    responses={
        200: {"description": "Prediction returned successfully."},
        422: {"description": "Validation error — check request schema."},
        500: {"description": "Internal inference error."},
    },
)
def predict_replenishment(request: ReplenishmentRequest):
    """
    Runs the XGBoost replenishment classifier on the submitted inventory telemetry.

    **Returns:**
    - `urgent_reorder` — `true` if the model predicts an urgent reorder is needed
    - `confidence_score` — model's probability estimate (0.0 – 1.0)
    - `action` — recommended action string
    - `sku_id` and `store_id` echoed back for traceability

    **Feature notes:**
    - `available` and `reorder_level` are intentionally **excluded** from the model
      to prevent data leakage — do not pass them.
    - `store_id` and `temp_zone` are accepted as plain strings and one-hot encoded
      internally before hitting the model.
    """
    result = inference_service.predict(request)
    return result
