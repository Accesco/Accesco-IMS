import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.modules.audit.service import AuditLogService
from app.modules.audit.schemas import AuditLogCreate

@pytest_asyncio.fixture
async def setup_audit_data(db_session: AsyncSession):
    service = AuditLogService(db_session)
    # Create some dummy logs
    log1 = await service.log_action(
        module="TestModule",
        action="TEST_ACTION_1",
        user_id=1,
        entity_id="entity-1",
        old_values={"status": "inactive"},
        new_values={"status": "active"}
    )
    
    log2 = await service.log_action(
        module="TestModule",
        action="TEST_ACTION_2",
        user_id=2,
        entity_id="entity-2",
        new_values={"score": 100}
    )
    
    await db_session.commit()
    
    return log1, log2


@pytest.mark.asyncio
async def test_log_action(db_session: AsyncSession):
    service = AuditLogService(db_session)
    log = await service.log_action(
        module="Auth",
        action="LOGIN",
        user_id=123,
        metadata_info={"ip": "127.0.0.1"}
    )
    await db_session.commit()
    
    assert log.id is not None
    assert log.module == "Auth"
    assert log.action == "LOGIN"
    assert log.user_id == 123
    assert log.metadata_info == {"ip": "127.0.0.1"}


@pytest.mark.asyncio
async def test_get_log_by_id(db_session: AsyncSession, setup_audit_data):
    log1, _ = setup_audit_data
    service = AuditLogService(db_session)
    
    fetched_log = await service.get_log_by_id(log1.id)
    assert fetched_log.id == log1.id
    assert fetched_log.action == "TEST_ACTION_1"


@pytest.mark.asyncio
async def test_get_all_logs(db_session: AsyncSession, setup_audit_data):
    service = AuditLogService(db_session)
    
    # Get all
    all_logs = await service.get_all_logs(module="TestModule")
    assert len(all_logs) >= 2
    
    # Filter by user
    user1_logs = await service.get_all_logs(user_id=1)
    assert len(user1_logs) == 1
    assert user1_logs[0].action == "TEST_ACTION_1"
    
    # Filter by action
    action2_logs = await service.get_all_logs(action="TEST_ACTION_2")
    assert len(action2_logs) == 1
    assert action2_logs[0].user_id == 2
