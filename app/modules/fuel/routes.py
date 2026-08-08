from fastapi import APIRouter, Depends

from app.modules.auth.routes import RoleChecker
from app.modules.fuel.schemas import FuelEstimateRequest, FuelEstimateResponse
from app.modules.fuel.service import FuelEstimationService

router = APIRouter(prefix="/fuel", tags=["fuel"])

all_authorized = RoleChecker(["Admin", "StoreManager", "Viewer"])


@router.post(
    "/estimate",
    response_model=FuelEstimateResponse,
    summary="Estimate fuel consumption for a truck trip",
    description=(
        "Deterministic formula combining base consumption, load weight, "
        "a terrain proxy per lane, and an optional congestion penalty if "
        "an actual average speed is supplied. Stateless -- nothing persisted. "
        "Fuel price is caller-supplied (not hardcoded) since prices are "
        "volatile; omit it to get liters only, no cost figure."
    ),
)
async def estimate_fuel(
    request: FuelEstimateRequest,
    _current_user=Depends(all_authorized),
):
    service = FuelEstimationService()
    return service.estimate(request)
