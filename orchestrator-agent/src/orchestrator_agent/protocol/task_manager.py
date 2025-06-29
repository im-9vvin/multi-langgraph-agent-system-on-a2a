"""Task management for A2A protocol compliance."""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from ..common import get_logger
from ..common.exceptions import TaskError
from .models import TaskStatus, A2AMessage

logger = get_logger(__name__)


class TaskManager:
    """Manages task lifecycle for A2A compliance."""
    
    def __init__(self):
        self._tasks: Dict[str, TaskStatus] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
    
    async def create_task(self, message: A2AMessage) -> TaskStatus:
        """Create a new task."""
        task_id = str(uuid4())
        now = datetime.utcnow()
        
        task = TaskStatus(
            taskId=task_id,
            contextId=message.contextId or f"ctx-{task_id}",
            status="pending",
            createdAt=now,
            updatedAt=now
        )
        
        self._tasks[task_id] = task
        self._locks[task_id] = asyncio.Lock()
        
        logger.info("Created task", task_id=task_id)
        return task
    
    async def get_task(self, task_id: str) -> Optional[TaskStatus]:
        """Get task by ID."""
        return self._tasks.get(task_id)
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: str,
        error: Optional[str] = None,
        result: Optional[dict[str, Any]] = None
    ) -> Optional[TaskStatus]:
        """Update task status."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        async with self._locks[task_id]:
            task.status = status
            task.updatedAt = datetime.utcnow()
            
            if error:
                task.error = error
            if result:
                task.result = result
            
            logger.info("Updated task", task_id=task_id, status=status)
            return task
    
    async def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> list[TaskStatus]:
        """List tasks with optional filtering."""
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by creation time, newest first
        tasks.sort(key=lambda t: t.createdAt, reverse=True)
        
        return tasks[:limit]
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status in ["completed", "failed", "cancelled"]:
            return False
        
        await self.update_task_status(task_id, "cancelled")
        return True
    
    def cleanup_old_tasks(self, max_age_seconds: int = 3600):
        """Clean up old completed tasks."""
        now = datetime.utcnow()
        to_remove = []
        
        for task_id, task in self._tasks.items():
            if task.status in ["completed", "failed", "cancelled"]:
                age = (now - task.updatedAt).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._tasks[task_id]
            del self._locks[task_id]
        
        if to_remove:
            logger.info("Cleaned up old tasks", count=len(to_remove))