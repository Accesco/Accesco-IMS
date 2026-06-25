from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.service import AuditLogService

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])

# Only Admins can view audit logs
admin_only = RoleChecker(["Admin"])

@router.get("", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = None,
    module: Optional[str] = None,
    action: Optional[str] = None,
    entity_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_only)
):
    service = AuditLogService(db)
    return await service.get_all_logs(
        skip=skip,
        limit=limit,
        user_id=user_id,
        module=module,
        action=action,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_only)
):
    service = AuditLogService(db)
    return await service.get_log_by_id(log_id)
