from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.eta.schemas import ETAPredictRequest, ETAPredictionResponse
from app.modules.eta.service import ETAService

router = APIRouter(prefix="/eta", tags=["eta"])

# Role permission helpers.
# NOTE: reusing the existing Admin/StoreManager/Viewer roles for now,
# matching most other read-heavy modules -- flag to the team if TMS
# should get its own FleetManager/Dispatcher role instead.
all_authorized = RoleChecker(["Admin", "StoreManager", "Viewer"])


@router.post(
    "/predict",
    response_model=ETAPredictionResponse,
    summary="Predict and persist a corrected ETA for an in-transit shipment",
    description=(
        "Sends a telemetry snapshot to the ETA Drift Engine and persists "
        "the resulting prediction as a history log entry."
    ),
)
async def predict_eta(
    request: ETAPredictRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized),
):
    service = ETAService(db)
    return await service.predict(request)


@router.get(
    "/predictions",
    response_model=List[ETAPredictionResponse],
    summary="List ETA predictions",
    description="Retrieve logged ETA predictions, optionally filtered by shipment, lane, or carrier.",
)
async def get_predictions(
    shipment_id: Optional[str] = None,
    lane_id: Optional[str] = None,
    carrier_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized),
):
    service = ETAService(db)
    return await service.get_predictions(shipment_id, lane_id, carrier_id, skip, limit)


@router.get(
    "/predictions/{prediction_id}",
    response_model=ETAPredictionResponse,
    summary="Get a single ETA prediction",
    description="Retrieve a specific logged ETA prediction by ID.",
)
async def get_prediction(
    prediction_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized),
):
    service = ETAService(db)
    return await service.get_prediction_by_id(prediction_id)
