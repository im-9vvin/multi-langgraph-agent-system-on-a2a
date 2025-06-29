"""Task lifecycle management for A2A protocol."""

import asyncio
from typing import Dict, Optional, Any, Callable
from datetime import datetime
import logging

from .models import A2ATask, TaskStatus
from ..common.exceptions import TaskNotFoundError, InvalidTaskStateError


logger = logging.getLogger(__name__)


class TaskManager:
    """Manages A2A task lifecycle and state transitions."""
    
    def __init__(self, max_concurrent_tasks: int = 100):
        """Initialize task manager.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
        """
        self.tasks: Dict[str, A2ATask] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self._task_callbacks: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        
    async def create_task(self, 
                         task_id: str, 
                         input_data: Dict[str, Any],
                         metadata: Optional[Dict[str, Any]] = None) -> A2ATask:
        """Create a new task.
        
        Args:
            task_id: Unique task identifier
            input_data: Task input parameters
            metadata: Optional task metadata
            
        Returns:
            Created task
            
        Raises:
            ValueError: If task limit exceeded
        """
        async with self._lock:
            if len(self.tasks) >= self.max_concurrent_tasks:
                raise ValueError(f"Task limit exceeded: {self.max_concurrent_tasks}")
                
            task = A2ATask(
                task_id=task_id,
                input_data=input_data,
                metadata=metadata or {}
            )
            self.tasks[task_id] = task
            logger.info(f"Created task: {task_id}")
            return task
    
    async def get_task(self, task_id: str) -> A2ATask:
        """Get task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task instance
            
        Raises:
            TaskNotFoundError: If task not found
        """
        if task_id not in self.tasks:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        return self.tasks[task_id]
    
    async def update_task_status(self, 
                                task_id: str, 
                                status: TaskStatus,
                                output_data: Optional[Dict[str, Any]] = None,
                                error: Optional[str] = None) -> A2ATask:
        """Update task status.
        
        Args:
            task_id: Task identifier
            status: New task status
            output_data: Optional output data
            error: Optional error message
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task not found
            InvalidTaskStateError: If invalid state transition
        """
        async with self._lock:
            task = await self.get_task(task_id)
            
            # Validate state transition
            if not self._is_valid_transition(task.status, status):
                raise InvalidTaskStateError(
                    f"Invalid transition from {task.status} to {status}"
                )
            
            # Update task
            task.status = status
            task.updated_at = datetime.utcnow()
            
            if output_data is not None:
                task.output_data = output_data
                
            if error is not None:
                task.error = error
                
            logger.info(f"Updated task {task_id} status to {status}")
            
            # Trigger callback if registered
            if task_id in self._task_callbacks:
                await self._task_callbacks[task_id](task)
                
            return task
    
    async def delete_task(self, task_id: str) -> None:
        """Delete a task.
        
        Args:
            task_id: Task identifier
            
        Raises:
            TaskNotFoundError: If task not found
        """
        async with self._lock:
            if task_id not in self.tasks:
                raise TaskNotFoundError(f"Task not found: {task_id}")
                
            del self.tasks[task_id]
            if task_id in self._task_callbacks:
                del self._task_callbacks[task_id]
                
            logger.info(f"Deleted task: {task_id}")
    
    async def list_tasks(self, 
                        status: Optional[TaskStatus] = None,
                        limit: int = 100) -> list[A2ATask]:
        """List tasks with optional filtering.
        
        Args:
            status: Optional status filter
            limit: Maximum number of tasks to return
            
        Returns:
            List of tasks
        """
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
            
        # Sort by creation time, newest first
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]
    
    def register_callback(self, task_id: str, callback: Callable) -> None:
        """Register a callback for task status changes.
        
        Args:
            task_id: Task identifier
            callback: Async callback function
        """
        self._task_callbacks[task_id] = callback
        
    def _is_valid_transition(self, current: TaskStatus, new: TaskStatus) -> bool:
        """Check if status transition is valid.
        
        Args:
            current: Current status
            new: New status
            
        Returns:
            True if transition is valid
        """
        # Define valid transitions
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.PROCESSING, TaskStatus.CANCELLED],
            TaskStatus.PROCESSING: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.COMPLETED: [],  # Terminal state
            TaskStatus.FAILED: [],      # Terminal state
            TaskStatus.CANCELLED: []    # Terminal state
        }
        
        return new in valid_transitions.get(current, [])