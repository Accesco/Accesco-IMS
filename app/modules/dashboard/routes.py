from fastapi import APIRouter, Depends, Query, status, WebSocket, WebSocketDisconnect
from typing import Optional
from app.core.security import decode_access_token

from app.modules.dashboard.schemas import (
    StandardResponse,
    DashboardSummaryResponse,
    RevenueChartResponse,
    OrdersChartResponse,
    InventoryChartResponse,
    WarehousePerformanceResponse,
    ActivitiesResponse,
    AlertsResponse,
    DashboardFilterParams,
    PaginationParams
)
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.service import DashboardService
from app.modules.dashboard.notifier import get_connection_manager, ConnectionManager
from app.modules.auth.routes import get_current_user
from app.models.auth import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get(
    "/summary",
    response_model=StandardResponse[DashboardSummaryResponse],
    summary="Get Dashboard Summary",
    description="Retrieves the main dashboard KPIs (orders, revenue, SLA, inventory accuracy, etc.).",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"}
    }
)
async def get_summary(
    filters: DashboardFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    data = await service.get_summary(filters.model_dump(exclude_unset=True))
    return StandardResponse(
        message="Dashboard summary retrieved successfully",
        data=data
    )

@router.get(
    "/charts/revenue",
    response_model=StandardResponse[RevenueChartResponse],
    summary="Get Revenue Chart Data",
    description="Retrieves revenue trends (daily, weekly, monthly, yearly).",
    responses={401: {"description": "Not authenticated"}, 500: {"description": "Internal server error"}}
)
async def get_revenue_chart(
    filters: DashboardFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    data = await service.get_revenue_charts(filters.model_dump(exclude_unset=True))
    return StandardResponse(
        message="Revenue chart data retrieved successfully",
        data=data
    )

@router.get(
    "/charts/orders",
    response_model=StandardResponse[OrdersChartResponse],
    summary="Get Orders Chart Data",
    description="Retrieves order status counts for charting.",
    responses={401: {"description": "Not authenticated"}, 500: {"description": "Internal server error"}}
)
async def get_orders_chart(
    filters: DashboardFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    data = await service.get_orders_chart(filters.model_dump(exclude_unset=True))
    return StandardResponse(
        message="Orders chart data retrieved successfully",
        data=data
    )

@router.get(
    "/charts/inventory",
    response_model=StandardResponse[InventoryChartResponse],
    summary="Get Inventory Chart Data",
    description="Retrieves inventory distribution for charting.",
    responses={401: {"description": "Not authenticated"}, 500: {"description": "Internal server error"}}
)
async def get_inventory_chart(
    filters: DashboardFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    data = await service.get_inventory_chart(filters.model_dump(exclude_unset=True))
    return StandardResponse(
        message="Inventory chart data retrieved successfully",
        data=data
    )

@router.get(
    "/warehouses",
    response_model=StandardResponse[WarehousePerformanceResponse],
    summary="Get Warehouse Performance",
    description="Retrieves performance metrics grouped by warehouse.",
    responses={401: {"description": "Not authenticated"}, 500: {"description": "Internal server error"}}
)
async def get_warehouses(
    filters: DashboardFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    data = await service.get_warehouses(filters.model_dump(exclude_unset=True))
    return StandardResponse(
        message="Warehouse performance data retrieved successfully",
        data=data
    )

@router.get(
    "/activities",
    response_model=StandardResponse[ActivitiesResponse],
    summary="Get Recent Activities",
    description="Retrieves paginated recent activities from the audit log.",
    responses={401: {"description": "Not authenticated"}, 500: {"description": "Internal server error"}}
)
async def get_activities(
    pagination: PaginationParams = Depends(),
    filters: DashboardFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    data = await service.get_activities(
        limit=pagination.page_size,
        offset=(pagination.page - 1) * pagination.page_size,
        filters=filters.model_dump(exclude_unset=True)
    )
    return StandardResponse(
        message="Activities retrieved successfully",
        data=data
    )

@router.get(
    "/alerts",
    response_model=StandardResponse[AlertsResponse],
    summary="Get Active Alerts",
    description="Retrieves paginated active alerts.",
    responses={401: {"description": "Not authenticated"}, 500: {"description": "Internal server error"}}
)
async def get_alerts(
    pagination: PaginationParams = Depends(),
    filters: DashboardFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    data = await service.get_alerts(
        limit=pagination.page_size,
        offset=(pagination.page - 1) * pagination.page_size,
        filters=filters.model_dump(exclude_unset=True)
    )
    return StandardResponse(
        message="Alerts retrieved successfully",
        data=data
    )

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    manager: ConnectionManager = Depends(get_connection_manager)
):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for incoming messages (if any) or just wait for disconnect
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

