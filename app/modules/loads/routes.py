from fastapi import APIRouter, Depends

from app.modules.auth.routes import RoleChecker
from app.modules.loads.schemas import ConsolidationRequest, ConsolidationResponse
from app.modules.loads.service import LoadConsolidationService

router = APIRouter(prefix="/loads", tags=["loads"])

# NOTE: reusing Admin/StoreManager/Viewer, matching the eta module --
# flag to the team if TMS should get its own FleetManager/Dispatcher role.
all_authorized = RoleChecker(["Admin", "StoreManager", "Viewer"])


@router.post(
    "/consolidate",
    response_model=ConsolidationResponse,
    summary="Compute a truck load consolidation plan",
    description=(
        "Bin-packs a set of ERP orders into truck loads, respecting the "
        "18,000 kg / 60 CBM capacity ceiling per truck, grouped by lane, "
        "with stops ordered by delivery deadline. Stateless -- computes "
        "and returns the plan, nothing is persisted."
    ),
)
async def consolidate(
    request: ConsolidationRequest,
    _current_user=Depends(all_authorized),
):
    service = LoadConsolidationService()
    return service.consolidate(request.orders)
