
from __future__ import annotations

import time
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis_client
from app.modules.auth.routes import RoleChecker
from app.modules.dispatch import service
from app.modules.dispatch.schemas import DispatchResponse
from app.modules.dispatch.optimizer_service import GlobalDispatchOptimizer
from app.models.rider import Rider

logger = logging.getLogger("dispatch_engine")

router = APIRouter(prefix="/dispatch", tags=["Dispatch Engine"])

# Role guard helpers (from app/modules/riders/routes.py)
admin_or_manager = RoleChecker(["Admin", "StoreManager"])
admin_only = RoleChecker(["Admin"])
viewer_roles = RoleChecker(["Admin", "StoreManager", "Viewer"])


@router.post("/assign/{order_id}", response_model=DispatchResponse)
async def assign_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_manager),
):
    start = time.monotonic()
    res = await service.ingest_new_order(db, order_id)
    duration_ms = (time.monotonic() - start) * 1000

    # Persist latency sample 
    await service.record_dispatch_latency(db, "/dispatch/assign", duration_ms)

    return {
        "order_id": order_id,
        "rider_id": res.get("offered_rider_id", 0),
        "status": res.get("status", "QUEUED"),
    }


@router.post("/rider/respond")
async def respond_to_assignment(
    rider_id: int = Body(...),
    order_id: Optional[int] = Body(None),
    batch_id: Optional[int] = Body(None),
    accepted: bool = Body(...),
    db: AsyncSession = Depends(get_db),
    # TODO: replace with rider-token auth when rider-scoped JWT is added
    _current_user=Depends(admin_or_manager),
):
    return await service.respond_to_assignment(db, rider_id, order_id, batch_id, accepted)


@router.post("/rider/heartbeat")
async def process_heartbeat(
    rider_id: int = Body(...),
    latitude: float = Body(...),
    longitude: float = Body(...),
    battery_level: float = Body(...),
    db: AsyncSession = Depends(get_db),
    # TODO: replace with rider-token auth when rider-scoped JWT is added
    _current_user=Depends(admin_or_manager),
):
    await service.record_heartbeat(db, rider_id, latitude, longitude, battery_level)
    return {"status": "HEARTBEAT_RECORDED"}


@router.post("/rider/transition")
async def force_transition_state(
    rider_id: int = Body(...),
    target_state: str = Body(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_manager),
):
    from app.core.exceptions import ResourceNotFoundException
    rider = await db.get(Rider, rider_id)
    if not rider:
        raise ResourceNotFoundException("Rider not found")

    await service.update_rider_state(db, rider, target_state, trigger="API_MANUAL_TRANSITION")
    await db.commit()
    return {"status": "TRANSITION_SUCCESSFUL", "current_state": rider.status}


@router.get("/batches")
async def list_active_batches(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(viewer_roles),
):
    return await service.get_all_active_batches(db)


@router.get("/batches/{batch_id}")
async def get_batch_details(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(viewer_roles),
):
    return await service.get_batch_details(db, batch_id)


# SECURED OPTIMIZATION ENDPOINT

@router.post("/optimize")
async def trigger_global_optimization(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
    _current_user=Depends(admin_or_manager),
):
    optimizer = GlobalDispatchOptimizer(db, redis)
    assignments_made = await optimizer.execute_global_optimization_sweep()
    return {
        "status": "OPTIMIZATION_SWEEP_EXECUTED",
        "assignments_committed": assignments_made,
    }


@router.post("/sweep")
async def trigger_manual_sweep(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_only),
):
    await service.execute_manual_sweep(db)
    return {"status": "SWEEP_CYCLE_EXECUTED"}


# ─── Accuracy Metric Endpoints ───

@router.get("/metrics/assignment-accuracy")
async def get_assignment_accuracy(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_manager),
):
    from app.modules.dispatch.metrics_service import MetricsService
    svc = MetricsService(db)
    return await svc.assignment_accuracy()


@router.get("/metrics/batch-fill-rate")
async def get_batch_fill_rate(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_manager),
):
    from app.modules.dispatch.metrics_service import MetricsService
    svc = MetricsService(db)
    return await svc.batch_fill_rate()


@router.get("/metrics/on-time-rate")
async def get_on_time_rate(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_manager),
):
    from app.modules.dispatch.metrics_service import MetricsService
    svc = MetricsService(db)
    return await svc.on_time_rate()


@router.get("/metrics/forecast-mape")
async def get_forecast_mape(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_manager),
):
    from app.modules.dispatch.metrics_service import MetricsService
    svc = MetricsService(db)
    return await svc.forecast_mape()


@router.get("/metrics/rider-utilisation")
async def get_rider_utilisation(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_manager),
):
    from app.modules.dispatch.metrics_service import MetricsService
    svc = MetricsService(db)
    return await svc.rider_utilisation()