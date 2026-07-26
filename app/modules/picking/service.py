import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import ResourceNotFoundException, IMSException, ForbiddenException
from app.core.redis import RedisService
from app.core.events import create_outbox_event
from app.modules.picking.repository import PickingRepository
from app.modules.orders.repository import OrderRepository
from app.modules.audit.service import AuditLogService
from app.modules.websocket.events import publish_event
from app.models.picking import PickWave, PickTask, PickTaskItem
from app.models.order import Order

logger = logging.getLogger(__name__)

class TaskAlreadyAssignedException(IMSException):
    def __init__(self, message: str = "Task is already assigned"):
        super().__init__(message, 409)

class InvalidPickQuantityException(IMSException):
    def __init__(self, message: str = "Invalid pick quantity"):
        super().__init__(message, 400)

class TaskIncompleteException(IMSException):
    def __init__(self, message: str = "Task is incomplete"):
        super().__init__(message, 400)

class PickingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PickingRepository(db)
        self.order_repo = OrderRepository(db)

    async def generate_wave(self, store_id: int, user_id: int) -> PickWave:
        """Finds all CONFIRMED orders for a store and groups them into a PickWave."""
        # Get confirmed orders for the store
        orders_result = await self.db.execute(
            select(Order).where(Order.store_id == store_id, Order.status == "CONFIRMED")
        )
        orders = orders_result.scalars().all()

        if not orders:
            raise IMSException("No CONFIRMED orders found for this store to generate a wave.", 400)

        # Create Wave
        wave = await self.repo.create_wave(store_id)

        tasks_to_create = []
        for order in orders:
            # Transition order to READY_FOR_PICKING
            order.status = "READY_FOR_PICKING"
            
            task = PickTask(
                wave_id=wave.id,
                order_id=order.id,
                status="PENDING"
            )
            tasks_to_create.append((task, order))

        # We must create tasks first to get their IDs
        db_tasks = [t[0] for t in tasks_to_create]
        await self.repo.create_tasks_bulk(db_tasks)

        items_to_create = []
        for task, order in tasks_to_create:
            # We need to eagerly load order items if they aren't loaded. 
            # In SQLAlchemy Async, accessing items might raise MissingGreenlet if not loaded.
            # Since OrderRepository doesn't always load items in basic select, let's load them explicitly if needed.
            # Actually, Order items might not be loaded. Let's fetch the full order.
            full_order = await self.order_repo.get_order_by_id(order.id)
            for order_item in full_order.items:
                pick_item = PickTaskItem(
                    pick_task_id=task.id,
                    order_item_id=order_item.id,
                    product_id=order_item.product_id,
                    expected_quantity=order_item.quantity,
                    picked_quantity=0
                )
                items_to_create.append(pick_item)

        await self.repo.create_task_items_bulk(items_to_create)

        await AuditLogService(self.db).log_action(
            module="Picking",
            action="GENERATE_WAVE",
            user_id=user_id,
            entity_id=str(wave.id),
            new_values={"store_id": store_id, "order_count": len(orders)}
        )

        await create_outbox_event(
            self.db,
            "picking.wave_created",
            {"wave_id": wave.id, "store_id": store_id, "order_count": len(orders)}
        )

        await self.db.commit()

        # Publish WebSocket event
        await publish_event(
            event_type="PICK_WAVE_CREATED",
            entity_type="pick_wave",
            entity_id=wave.id,
            data={"wave_id": wave.id, "store_id": store_id}
        )

        hydrated_wave = await self.repo.get_wave_by_id(wave.id)
        if not hydrated_wave:
            raise ResourceNotFoundException("Failed to load wave after creation")
        return hydrated_wave

    async def get_waves(self, store_id: Optional[int] = None) -> List[PickWave]:
        return await self.repo.get_waves(store_id)

    async def get_tasks(self, wave_id: Optional[int] = None, assignee_id: Optional[int] = None, status: Optional[str] = None) -> List[PickTask]:
        return await self.repo.get_tasks(wave_id, assignee_id, status)

    async def assign_task(self, task_id: int, user_id: int) -> PickTask:
        """Assign a task to a picker with Redis Distributed Locking + DB row locking."""
        from app.core.redis import redis_service
        lock_key = f"picking:task_assign:{task_id}"
        
        has_lock = False
        if redis_service.client is not None:
            has_lock = await redis_service.acquire_lock(lock_key, lock_timeout=10)
            if not has_lock:
                raise IMSException("Task is currently being modified by another user", 409)
                
        try:
            task = await self.repo.get_task_by_id(task_id, lock=True)
            if not task:
                raise ResourceNotFoundException("Pick task not found")
                
            if task.status != "PENDING":
                raise IMSException(f"Task is already {task.status}", 400)
                
            task.assigned_to = user_id
            task.status = "IN_PROGRESS"
            
            await self.repo.db.flush()
            
            # Publish event
            await publish_event(
                event_type="PICK_TASK_ASSIGNED",
                entity_type="pick_task",
                entity_id=task.id,
                data={"task_id": task.id, "assigned_to": user_id}
            )
            
            await self.repo.db.commit()
            
            hydrated_task = await self.repo.get_task_by_id(task.id)
            if not hydrated_task:
                 raise ResourceNotFoundException("Failed to load task after assignment")
            
            await AuditLogService(self.db).log_action(
                module="Picking",
                action="ASSIGN_TASK",
                user_id=user_id,
                entity_id=str(task.id),
                new_values={"assigned_to": user_id, "status": "IN_PROGRESS"}
            )

            await create_outbox_event(
                self.db,
                "picking.task_assigned",
                {"task_id": task.id, "assigned_to": user_id}
            )

            await self.db.commit()

            await publish_event(
                event_type="PICK_TASK_STATUS_CHANGED",
                entity_type="pick_task",
                entity_id=task.id,
                data={"task_id": task.id, "status": "IN_PROGRESS", "assigned_to": user_id}
            )

            return task
        finally:
            if has_lock and redis_service.client is not None:
                await redis_service.release_lock(lock_key)

    async def execute_pick(self, task_id: int, item_id: int, quantity: int, user_id: int) -> PickTaskItem:
        """Record physical pick action for an item."""
        if quantity <= 0:
            raise InvalidPickQuantityException("Quantity must be greater than 0")

        task = await self.repo.get_task_by_id(task_id, lock=True)
        if not task:
            raise ResourceNotFoundException("Pick Task not found")
            
        if task.assigned_to != user_id:
            raise ForbiddenException("You are not assigned to this pick task")

        if task.status != "IN_PROGRESS":
            raise IMSException(f"Cannot pick items for task in status: {task.status}", 400)

        item = next((i for i in task.items if i.id == item_id), None)
        if not item:
            raise ResourceNotFoundException("Pick Task Item not found in this task")

        new_quantity = item.picked_quantity + quantity
        if new_quantity > item.expected_quantity:
            raise InvalidPickQuantityException(
                f"Cannot pick {quantity}. Expected: {item.expected_quantity}, Already picked: {item.picked_quantity}"
            )

        old_quantity = item.picked_quantity
        item.picked_quantity = new_quantity

        await AuditLogService(self.db).log_action(
            module="Picking",
            action="PICK_ITEM",
            user_id=user_id,
            entity_id=str(item.id),
            old_values={"picked_quantity": old_quantity},
            new_values={"picked_quantity": new_quantity}
        )

        await self.db.commit()
        return item

    async def complete_task(self, task_id: int, user_id: int) -> PickTask:
        """Finalize the task, ensuring all items are fully picked."""
        task = await self.repo.get_task_by_id(task_id, lock=True)
        if not task:
            raise ResourceNotFoundException("Pick Task not found")

        if task.assigned_to != user_id:
            raise ForbiddenException("You are not assigned to this pick task")

        if task.status != "IN_PROGRESS":
            raise IMSException(f"Cannot complete task in status: {task.status}", 400)

        # Validate all items are fully picked
        for item in task.items:
            if item.picked_quantity < item.expected_quantity:
                raise TaskIncompleteException(
                    f"Item {item.product_id} is incomplete. Picked {item.picked_quantity}/{item.expected_quantity}"
                )

        task.status = "COMPLETED"

        # Gather order_items mapping for the kafka consumer to process stock deductions
        picked_items = [
            {"order_item_id": item.order_item_id, "product_id": item.product_id, "quantity": item.picked_quantity}
            for item in task.items
        ]

        await AuditLogService(self.db).log_action(
            module="Picking",
            action="COMPLETE_TASK",
            user_id=user_id,
            entity_id=str(task.id),
            new_values={"status": "COMPLETED"}
        )

        await create_outbox_event(
            self.db,
            "picking.task_completed",
            {
                "task_id": task.id, 
                "wave_id": task.wave_id, 
                "order_id": task.order_id,
                "items": picked_items
            }
        )

        await self.db.flush()

        # Check if wave is completed
        uncompleted_tasks_count = await self.repo.get_uncompleted_tasks_count(task.wave_id)
        if uncompleted_tasks_count == 0:
            await self._complete_wave(task.wave_id, user_id)

        await self.db.commit()

        await publish_event(
            event_type="PICK_TASK_STATUS_CHANGED",
            entity_type="pick_task",
            entity_id=task.id,
            data={"task_id": task.id, "status": "COMPLETED"}
        )

        return task

    async def _complete_wave(self, wave_id: int, user_id: int) -> None:
        """Internal method to complete a wave when all tasks are done."""
        wave = await self.repo.get_wave_by_id(wave_id)
        if not wave:
            return

        wave.status = "COMPLETED"
        
        # Transition all associated orders to READY_FOR_DISPATCH
        for task in wave.tasks:
            order = await self.order_repo.get_order_by_id_for_update(task.order_id)
            if order and order.status == "READY_FOR_PICKING":
                order.status = "READY_FOR_DISPATCH"
                
                await create_outbox_event(
                    self.db,
                    "orders.status_changed",
                    {
                        "order_id": order.id,
                        "old_status": "READY_FOR_PICKING",
                        "new_status": "READY_FOR_DISPATCH",
                    },
                )
                
                await publish_event(
                    event_type="ORDER_STATUS_CHANGED",
                    entity_type="order",
                    entity_id=order.id,
                    data={"order_id": order.id, "old_status": "READY_FOR_PICKING", "new_status": "READY_FOR_DISPATCH"}
                )

        await AuditLogService(self.db).log_action(
            module="Picking",
            action="COMPLETE_WAVE",
            user_id=user_id,
            entity_id=str(wave.id),
            new_values={"status": "COMPLETED"}
        )
