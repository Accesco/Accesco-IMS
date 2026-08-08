from fastapi import APIRouter, Depends

from app.modules.auth.routes import RoleChecker
from app.modules.maintenance.schemas import MaintenancePredictRequest, MaintenancePredictResponse
from app.modules.maintenance.service import MaintenanceService

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

all_authorized = RoleChecker(["Admin", "StoreManager", "Viewer"])


@router.post(
    "/predict",
    response_model=MaintenancePredictResponse,
    summary="Predict corrected remaining distance until vehicle maintenance is due",
    description=(
        "Sends a vehicle usage snapshot to the Maintenance Drift Engine "
        "and returns a naive fixed-interval estimate, the model's "
        "predicted drift correction, and the corrected remaining "
        "distance. Stateless -- nothing persisted."
    ),
)
async def predict_maintenance(
    request: MaintenancePredictRequest,
    _current_user=Depends(all_authorized),
):
    service = MaintenanceService()
    return await service.predict(request)
