
from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis_client
from app.modules.auth.routes import RoleChecker
from app.modules.dispatch import service
from app.modules.dispatch.schemas import DispatchResponse
from app.modules.dispatch.optimizer_service import GlobalDispatchOptimizer
from app.models.rider import Rider

router = APIRouter(prefix="/dispatch", tags=["Dispatch Engine"])

admin_or_manager = RoleChecker(["Admin", "StoreManager"])


@router.post("/assign/{order_id}", response_model=DispatchResponse)
async def assign_order(order_id: int, db: AsyncSession = Depends(get_db)):
    res = await service.ingest_new_order(db, order_id)
    return {
        "order_id": order_id,
        "rider_id": res.get("offered_rider_id", 0),
        "status": res.get("status", "QUEUED")
    }


@router.post("/rider/respond")
async def respond_to_assignment(
    rider_id: int = Body(...),
    order_id: Optional[int] = Body(None),
    batch_id: Optional[int] = Body(None),
    accepted: bool = Body(...),
    db: AsyncSession = Depends(get_db)
):
    return await service.respond_to_assignment(db, rider_id, order_id, batch_id, accepted)


@router.post("/rider/heartbeat")
async def process_heartbeat(
    rider_id: int = Body(...),
    latitude: float = Body(...),
    longitude: float = Body(...),
    battery_level: float = Body(...),
    db: AsyncSession = Depends(get_db)
):
    await service.record_heartbeat(db, rider_id, latitude, longitude, battery_level)
    return {"status": "HEARTBEAT_RECORDED"}



@router.post("/rider/transition")
async def force_transition_state(
    rider_id: int = Body(...),
    target_state: str = Body(...),
    db: AsyncSession = Depends(get_db)
):
    from app.core.exceptions import ResourceNotFoundException
    rider = await db.get(Rider, rider_id)
    if not rider:
        raise ResourceNotFoundException("Rider not found")
        
    await service.update_rider_state(db, rider, target_state, trigger="API_MANUAL_TRANSITION")
    await db.commit()
    return {"status": "TRANSITION_SUCCESSFUL", "current_state": rider.status}


@router.get("/batches")
async def list_active_batches(db: AsyncSession = Depends(get_db)):
    return await service.get_all_active_batches(db)


@router.get("/batches/{batch_id}")
async def get_batch_details(batch_id: int, db: AsyncSession = Depends(get_db)):
    return await service.get_batch_details(db, batch_id)

# PHASE 3: SECURED OPTIMIZATION ENDPOINT

@router.post("/optimize")
async def trigger_global_optimization(
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis_client),
    _current_user = Depends(admin_or_manager) 
):
    optimizer = GlobalDispatchOptimizer(db, redis)
    assignments_made = await optimizer.execute_global_optimization_sweep()
    return {
        "status": "OPTIMIZATION_SWEEP_EXECUTED",
        "assignments_committed": assignments_made
    }


@router.post("/sweep")
async def trigger_manual_sweep(db: AsyncSession = Depends(get_db)):
    await service.execute_manual_sweep(db)
    return {"status": "SWEEP_CYCLE_EXECUTED"}