"""
Maintenance Drift Engine — FastAPI Inference Service
Accesco Living | TMS

Endpoint:  POST /predict-maintenance
Model:     GradientBoostingRegressor pipeline (maintenance_drift_model.joblib)

Predicts the "drift" between a naive fixed-interval maintenance
estimate ("every 10,000 km") and the actual remaining distance until
service is genuinely needed, using usage-pattern signals: load,
driving harshness, terrain, vehicle age. See maintenance-engine/ for
training code and methodology.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from schemas import MaintenanceRequest, MaintenanceResponse, HealthResponse
from inference import MaintenanceInferenceService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

inference_service: MaintenanceInferenceService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global inference_service
    model_path = os.getenv("MODEL_PATH", "maintenance_drift_model.joblib")
    logger.info(f"Loading model from '{model_path}' ...")
    inference_service = MaintenanceInferenceService(model_path)
    logger.info(f"Model ready. Features: {inference_service.expected_features}")
    yield
    logger.info("Shutting down inference service.")


app = FastAPI(
    title="Maintenance Drift Engine",
    description=(
        "REST API for the Accesco Living TMS maintenance prediction model. "
        "Accepts a vehicle usage snapshot and returns a naive fixed-interval "
        "estimate, the model's predicted drift correction, and the "
        "corrected remaining distance until service is due."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return HealthResponse(
        status="ok",
        model_features=inference_service.expected_features,
    )


@app.post(
    "/predict-maintenance",
    response_model=MaintenanceResponse,
    tags=["Prediction"],
    summary="Predict corrected remaining distance until maintenance is due",
    responses={
        200: {"description": "Prediction returned successfully."},
        422: {"description": "Validation error — check request schema."},
        500: {"description": "Internal inference error."},
    },
)
def predict_maintenance(request: MaintenanceRequest):
    """
    Runs the maintenance drift model on the submitted usage snapshot.

    **Returns:**
    - `naive_km_remaining` — 10,000 - km_since_last_service (fixed-interval baseline)
    - `predicted_drift_km` — model's correction (typically negative: heavy
      usage means service is due sooner than the naive rule assumes)
    - `corrected_km_remaining` — naive + predicted_drift, the number to
      actually use for scheduling
    """
    result = inference_service.predict(request)
    return result
