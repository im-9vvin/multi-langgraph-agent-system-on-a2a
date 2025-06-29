"""Task management for A2A protocol compliance."""

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .models import A2ATask, TaskStatus, TaskYieldUpdate

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages A2A tasks lifecycle and state."""
    
    def __init__(self):
        """Initialize task manager."""
        self._tasks: Dict[str, A2ATask] = {}
        self._task_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._task_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def create_task(
        self,
        input_data: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> A2ATask:
        """Create a new task.
        
        Args:
            input_data: Task input data
            task_id: Optional task ID (generated if not provided)
            
        Returns:
            Created task
        """
        task_id = task_id or str(uuid.uuid4())
        
        async with self._lock:
            task = A2ATask(
                task_id=task_id,
                status=TaskStatus.PENDING,
                input_data=input_data
            )
            self._tasks[task_id] = task
            
            # Notify callbacks
            await self._notify_callbacks(task_id, "created", task)
            
            logger.info(f"Created task {task_id}")
            return task
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[A2ATask]:
        """Update task status.
        
        Args:
            task_id: Task ID
            status: New status
            output_data: Optional output data
            error: Optional error message
            
        Returns:
            Updated task or None if not found
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return None
            
            task.status = status
            task.updated_at = datetime.utcnow()
            
            if output_data is not None:
                task.output_data = output_data
            
            if error is not None:
                task.error = error
            
            # Notify callbacks
            await self._notify_callbacks(task_id, "status_updated", task)
            
            logger.info(f"Updated task {task_id} status to {status}")
            return task
    
    async def yield_task_update(
        self,
        task_id: str,
        data: Any,
        event_type: str = "yield"
    ) -> bool:
        """Yield a streaming update for a task.
        
        Args:
            task_id: Task ID
            data: Update data
            event_type: Type of event
            
        Returns:
            True if successful, False if task not found
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found for yield update")
            return False
        
        update = TaskYieldUpdate(
            task_id=task_id,
            event_type=event_type,
            data=data
        )
        
        # Add to task queue
        await self._task_queues[task_id].put(update)
        
        # Notify callbacks
        await self._notify_callbacks(task_id, "yield", update)
        
        return True
    
    async def get_task(self, task_id: str) -> Optional[A2ATask]:
        """Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task or None if not found
        """
        return self._tasks.get(task_id)
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[A2ATask]:
        """List tasks with optional filtering.
        
        Args:
            status: Optional status filter
            limit: Maximum number of tasks to return
            
        Returns:
            List of tasks
        """
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]
    
    async def get_task_updates(self, task_id: str) -> asyncio.Queue:
        """Get the update queue for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Update queue
        """
        return self._task_queues[task_id]
    
    def register_callback(self, task_id: str, callback: Callable):
        """Register a callback for task events.
        
        Args:
            task_id: Task ID (or "*" for all tasks)
            callback: Async callback function
        """
        self._task_callbacks[task_id].append(callback)
    
    async def _notify_callbacks(self, task_id: str, event: str, data: Any):
        """Notify registered callbacks.
        
        Args:
            task_id: Task ID
            event: Event type
            data: Event data
        """
        # Notify task-specific callbacks
        for callback in self._task_callbacks.get(task_id, []):
            try:
                await callback(task_id, event, data)
            except Exception as e:
                logger.error(f"Callback error for task {task_id}: {e}")
        
        # Notify global callbacks
        for callback in self._task_callbacks.get("*", []):
            try:
                await callback(task_id, event, data)
            except Exception as e:
                logger.error(f"Global callback error: {e}")
    
    async def cleanup_task(self, task_id: str):
        """Clean up task resources.
        
        Args:
            task_id: Task ID
        """
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
            
            if task_id in self._task_queues:
                del self._task_queues[task_id]
            
            if task_id in self._task_callbacks:
                del self._task_callbacks[task_id]
            
            logger.info(f"Cleaned up task {task_id}")