# app/modules/dispatch/routes.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.dispatch import service
from app.modules.dispatch.schemas import DispatchResponse, DispatchStatusResponse
from app.modules.auth.routes import RoleChecker
from app.models.rider import Rider

router = APIRouter(prefix="/dispatch", tags=["Dispatch Engine"])

admin_or_store_manager = RoleChecker(["Admin", "StoreManager"])


@router.post("/assign/{order_id}", response_model=DispatchResponse)
async def assign_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
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
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    return await service.respond_to_assignment(db, rider_id, order_id, batch_id, accepted)


@router.post("/rider/heartbeat")
async def process_heartbeat(
    rider_id: int = Body(...),
    latitude: float = Body(...),
    longitude: float = Body(...),
    battery_level: float = Body(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    await service.record_heartbeat(db, rider_id, latitude, longitude, battery_level)
    return {"status": "HEARTBEAT_RECORDED"}


@router.post("/rider/transition")
async def force_transition_state(
    rider_id: int = Body(...),
    target_state: str = Body(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    rider = await db.get(Rider, rider_id)
    await service.update_rider_state(db, rider, target_state, trigger="API_MANUAL_TRANSITION")
    await db.commit()
    return {"status": "TRANSITION_SUCCESSFUL", "current_state": rider.status}


@router.get("/batches")
async def list_active_batches(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    """Retrieve all active batches currently in the dispatch engine."""
    return await service.get_all_active_batches(db)


@router.get("/batches/{batch_id}")
async def get_batch_details(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    """Retrieve detailed orders inside a specific batch."""
    return await service.get_batch_details(db, batch_id)


@router.post("/sweep")
async def trigger_manual_sweep(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    """Manually trigger the background sweep cycle for testing timeouts/SLA [14.1]."""
    await service.execute_manual_sweep(db)
    return {"status": "SWEEP_CYCLE_EXECUTED"}


# ─── Dispatch Lifecycle Endpoints ─────────────────────────────────────────────

@router.post("/{order_id}/pickup", response_model=DispatchStatusResponse)
async def pickup_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    """Mark an assigned order as picked up by the rider."""
    order = await service.pickup_order(db, order_id, user_id=_current_user.id)
    return DispatchStatusResponse(
        order_id=order.id, rider_id=order.rider_id,
        order_status=order.status, rider_status="EN_ROUTE_PICKUP",
        message="Order picked up by rider",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/{order_id}/in-transit", response_model=DispatchStatusResponse)
async def start_transit(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    """Mark an order as in transit (rider delivering)."""
    order = await service.start_transit(db, order_id, user_id=_current_user.id)
    return DispatchStatusResponse(
        order_id=order.id, rider_id=order.rider_id,
        order_status=order.status, rider_status="DELIVERING",
        message="Order is in transit",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/{order_id}/delivered", response_model=DispatchStatusResponse)
async def deliver_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    """Mark an order as delivered. Releases the rider."""
    order = await service.deliver_order(db, order_id, user_id=_current_user.id)
    return DispatchStatusResponse(
        order_id=order.id, rider_id=order.rider_id,
        order_status=order.status, rider_status="RETURNING",
        message="Order delivered successfully",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/{order_id}/failed", response_model=DispatchStatusResponse)
async def fail_delivery(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager),
):
    """Mark a delivery as failed. Releases the rider."""
    order = await service.fail_delivery(db, order_id, user_id=_current_user.id)
    return DispatchStatusResponse(
        order_id=order.id, rider_id=order.rider_id,
        order_status=order.status, rider_status="IDLE",
        message="Delivery failed",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )