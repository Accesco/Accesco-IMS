from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.core.exceptions import ResourceNotFoundException
from app.models.audit import AuditLog
from app.modules.audit.repository import AuditLogRepository
from app.modules.audit.schemas import AuditLogCreate

class AuditLogService:
    def __init__(self, db: AsyncSession):
        self.repo = AuditLogRepository(db)

    async def log_action(
        self,
        module: str,
        action: str,
        user_id: Optional[int] = None,
        entity_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata_info: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Logs a system action. Since it is often called within an existing transaction, 
        it does NOT commit the transaction by default. The caller is responsible for committing.
        """
        log_data = AuditLogCreate(
            user_id=user_id,
            module=module,
            action=action,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            metadata_info=metadata_info
        )
        return await self.repo.create_log(log_data)

    async def get_log_by_id(self, log_id: int) -> AuditLog:
        log = await self.repo.get_log_by_id(log_id)
        if not log:
            raise ResourceNotFoundException(f"Audit Log with ID {log_id} not found")
        return log

    async def get_all_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None,
        module: Optional[str] = None,
        action: Optional[str] = None,
        entity_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditLog]:
        return await self.repo.get_logs(
            skip=skip,
            limit=limit,
            user_id=user_id,
            module=module,
            action=action,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date
        )
