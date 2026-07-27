from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.routes import get_current_user, RoleChecker
from app.models.auth import User
from app.modules.picking.schemas import PickWaveResponse, PickTaskResponse, PickActionRequest, PickTaskItemResponse
from app.modules.picking.service import PickingService

router = APIRouter(prefix="/picking", tags=["Picking Engine"])

# Role Checkers
allow_wave_generation = RoleChecker(["Admin", "StoreManager"])
allow_task_execution = RoleChecker(["Admin", "WarehouseStaff"])

@router.post("/waves/generate", response_model=PickWaveResponse, status_code=status.HTTP_201_CREATED)
async def generate_wave(
    store_id: int = Query(..., description="The Dark Store ID to generate a wave for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(allow_wave_generation)
):
    """
    Generates a new Pick Wave by aggregating all CONFIRMED orders for the specified store.
    """
    service = PickingService(db)
    return await service.generate_wave(store_id=store_id, user_id=current_user.id)


@router.get("/waves", response_model=List[PickWaveResponse])
async def list_waves(
    store_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all pick waves, optionally filtered by store_id.
    """
    service = PickingService(db)
    return await service.get_waves(store_id=store_id)


@router.get("/tasks", response_model=List[PickTaskResponse])
async def list_tasks(
    wave_id: Optional[int] = Query(None),
    assignee_id: Optional[int] = Query(None),
    task_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List pick tasks based on filters.
    """
    service = PickingService(db)
    return await service.get_tasks(wave_id=wave_id, assignee_id=assignee_id, status=task_status)


@router.post("/tasks/{task_id}/assign", response_model=PickTaskResponse)
async def assign_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(allow_task_execution)
):
    """
    Assign a pick task to the current user (Picker).
    """
    service = PickingService(db)
    return await service.assign_task(task_id=task_id, user_id=current_user.id)


@router.post("/tasks/{task_id}/items/{item_id}/pick", response_model=PickTaskItemResponse)
async def pick_item(
    task_id: int,
    item_id: int,
    request: PickActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(allow_task_execution)
):
    """
    Record that a specific quantity of an item has been physically picked.
    """
    service = PickingService(db)
    return await service.execute_pick(
        task_id=task_id, 
        item_id=item_id, 
        quantity=request.quantity, 
        user_id=current_user.id
    )


@router.post("/tasks/{task_id}/complete", response_model=PickTaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(allow_task_execution)
):
    """
    Mark a pick task as COMPLETED. Validates that all items are fully picked.
    """
    service = PickingService(db)
    return await service.complete_task(task_id=task_id, user_id=current_user.id)
