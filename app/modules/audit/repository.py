from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.audit import AuditLog
from app.modules.audit.schemas import AuditLogCreate

class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(self, log_data: AuditLogCreate) -> AuditLog:
        db_log = AuditLog(
            user_id=log_data.user_id,
            module=log_data.module,
            action=log_data.action,
            entity_id=log_data.entity_id,
            old_values=log_data.old_values,
            new_values=log_data.new_values,
            metadata_info=log_data.metadata_info
        )
        self.db.add(db_log)
        # We don't commit here. The service layer calling this should handle transactions.
        await self.db.flush()
        return db_log

    async def get_log_by_id(self, log_id: int) -> Optional[AuditLog]:
        result = await self.db.execute(select(AuditLog).where(AuditLog.id == log_id))
        return result.scalar_one_or_none()

    async def get_logs(
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
        
        query = select(AuditLog)
        
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        if module is not None:
            query = query.where(AuditLog.module == module)
        if action is not None:
            query = query.where(AuditLog.action == action)
        if entity_id is not None:
            query = query.where(AuditLog.entity_id == entity_id)
        if start_date is not None:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            query = query.where(AuditLog.created_at <= end_date)
            
        query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
