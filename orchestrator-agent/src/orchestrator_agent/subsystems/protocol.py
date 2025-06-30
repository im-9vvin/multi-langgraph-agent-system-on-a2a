"""Protocol subsystem for full A2A protocol support."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from ..common.exceptions import OrchestratorError
from ..common.logging import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """A2A message types."""
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    CANCEL = "cancel"
    STATUS = "status"
    PROGRESS = "progress"


class TaskStatus(Enum):
    """Task status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProtocolMessage:
    """A2A protocol message."""
    
    def __init__(self, message_type: MessageType, data: Dict[str, Any],
                 task_id: Optional[str] = None, context_id: Optional[str] = None):
        """Initialize protocol message.
        
        Args:
            message_type: Type of message
            data: Message data
            task_id: Optional task ID
            context_id: Optional context ID
        """
        self.id = str(uuid.uuid4())
        self.type = message_type
        self.data = data
        self.task_id = task_id
        self.context_id = context_id
        self.timestamp = datetime.now().isoformat()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary following A2A spec."""
        message = {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data
        }
        
        if self.task_id:
            message["taskId"] = self.task_id
            
        if self.context_id:
            message["contextId"] = self.context_id
            
        return message
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolMessage":
        """Create from dictionary."""
        return cls(
            message_type=MessageType(data["type"]),
            data=data.get("data", {}),
            task_id=data.get("taskId"),
            context_id=data.get("contextId")
        )


class Task:
    """Represents an A2A task."""
    
    def __init__(self, task_id: str, request: str, 
                 context_id: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize task.
        
        Args:
            task_id: Unique task ID
            request: Task request
            context_id: Optional context ID
            metadata: Optional task metadata
        """
        self.id = task_id
        self.request = request
        self.context_id = context_id
        self.metadata = metadata or {}
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.progress = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    def update_status(self, status: TaskStatus):
        """Update task status."""
        self.status = status
        self.updated_at = datetime.now()
        
    def add_progress(self, progress: Dict[str, Any]):
        """Add progress update."""
        self.progress.append({
            "timestamp": datetime.now().isoformat(),
            "data": progress
        })
        self.updated_at = datetime.now()
        
    def complete(self, result: Any):
        """Mark task as completed."""
        self.result = result
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.now()
        
    def fail(self, error: str):
        """Mark task as failed."""
        self.error = error
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "request": self.request,
            "contextId": self.context_id,
            "metadata": self.metadata,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat()
        }


class ProtocolHandler:
    """Handles A2A protocol operations."""
    
    def __init__(self):
        """Initialize protocol handler."""
        self._tasks: Dict[str, Task] = {}
        self._message_handlers = {
            MessageType.TASK: self._handle_task_message,
            MessageType.CANCEL: self._handle_cancel_message,
            MessageType.STATUS: self._handle_status_message
        }
        
    def create_task_message(self, request: str, 
                          context_id: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> ProtocolMessage:
        """Create a task message.
        
        Args:
            request: Task request
            context_id: Optional context ID
            metadata: Optional metadata
            
        Returns:
            Protocol message for the task
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id, request, context_id, metadata)
        self._tasks[task_id] = task
        
        return ProtocolMessage(
            message_type=MessageType.TASK,
            data={
                "request": request,
                "metadata": metadata or {}
            },
            task_id=task_id,
            context_id=context_id
        )
        
    def create_result_message(self, task_id: str, result: Any) -> ProtocolMessage:
        """Create a result message.
        
        Args:
            task_id: Task ID
            result: Task result
            
        Returns:
            Protocol message for the result
        """
        task = self._tasks.get(task_id)
        if not task:
            raise OrchestratorError(f"Unknown task ID: {task_id}")
            
        task.complete(result)
        
        return ProtocolMessage(
            message_type=MessageType.RESULT,
            data={"result": result},
            task_id=task_id,
            context_id=task.context_id
        )
        
    def create_error_message(self, task_id: str, error: str,
                           error_type: Optional[str] = None) -> ProtocolMessage:
        """Create an error message.
        
        Args:
            task_id: Task ID
            error: Error message
            error_type: Optional error type
            
        Returns:
            Protocol message for the error
        """
        task = self._tasks.get(task_id)
        if not task:
            raise OrchestratorError(f"Unknown task ID: {task_id}")
            
        task.fail(error)
        
        return ProtocolMessage(
            message_type=MessageType.ERROR,
            data={
                "error": error,
                "type": error_type or "OrchestratorError"
            },
            task_id=task_id,
            context_id=task.context_id
        )
        
    def create_progress_message(self, task_id: str, 
                              progress: Dict[str, Any]) -> ProtocolMessage:
        """Create a progress message.
        
        Args:
            task_id: Task ID
            progress: Progress data
            
        Returns:
            Protocol message for the progress
        """
        task = self._tasks.get(task_id)
        if not task:
            raise OrchestratorError(f"Unknown task ID: {task_id}")
            
        task.add_progress(progress)
        
        return ProtocolMessage(
            message_type=MessageType.PROGRESS,
            data=progress,
            task_id=task_id,
            context_id=task.context_id
        )
        
    def handle_message(self, message: Dict[str, Any]) -> Optional[ProtocolMessage]:
        """Handle incoming protocol message.
        
        Args:
            message: Message dictionary
            
        Returns:
            Response message if any
        """
        try:
            proto_msg = ProtocolMessage.from_dict(message)
            handler = self._message_handlers.get(proto_msg.type)
            
            if handler:
                return handler(proto_msg)
            else:
                logger.warning(f"No handler for message type: {proto_msg.type}")
                return None
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return ProtocolMessage(
                message_type=MessageType.ERROR,
                data={
                    "error": str(e),
                    "type": "MessageHandlingError"
                }
            )
            
    def _handle_task_message(self, message: ProtocolMessage) -> Optional[ProtocolMessage]:
        """Handle task message."""
        # Create task from message
        task = Task(
            task_id=message.task_id or str(uuid.uuid4()),
            request=message.data.get("request", ""),
            context_id=message.context_id,
            metadata=message.data.get("metadata", {})
        )
        self._tasks[task.id] = task
        
        # Return status message
        return ProtocolMessage(
            message_type=MessageType.STATUS,
            data={
                "status": task.status.value,
                "message": "Task received and queued"
            },
            task_id=task.id,
            context_id=task.context_id
        )
        
    def _handle_cancel_message(self, message: ProtocolMessage) -> Optional[ProtocolMessage]:
        """Handle cancel message."""
        task_id = message.task_id
        if not task_id or task_id not in self._tasks:
            return ProtocolMessage(
                message_type=MessageType.ERROR,
                data={
                    "error": f"Unknown task ID: {task_id}",
                    "type": "InvalidTaskId"
                }
            )
            
        task = self._tasks[task_id]
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            return ProtocolMessage(
                message_type=MessageType.ERROR,
                data={
                    "error": f"Cannot cancel task in status: {task.status.value}",
                    "type": "InvalidOperation"
                },
                task_id=task_id
            )
            
        task.status = TaskStatus.CANCELLED
        return ProtocolMessage(
            message_type=MessageType.STATUS,
            data={
                "status": task.status.value,
                "message": "Task cancelled"
            },
            task_id=task_id,
            context_id=task.context_id
        )
        
    def _handle_status_message(self, message: ProtocolMessage) -> Optional[ProtocolMessage]:
        """Handle status request message."""
        task_id = message.task_id
        
        if task_id:
            # Status for specific task
            if task_id not in self._tasks:
                return ProtocolMessage(
                    message_type=MessageType.ERROR,
                    data={
                        "error": f"Unknown task ID: {task_id}",
                        "type": "InvalidTaskId"
                    }
                )
            task = self._tasks[task_id]
            return ProtocolMessage(
                message_type=MessageType.STATUS,
                data=task.to_dict(),
                task_id=task_id,
                context_id=task.context_id
            )
        else:
            # Status for all tasks
            context_id = message.context_id
            tasks = []
            
            for task in self._tasks.values():
                if not context_id or task.context_id == context_id:
                    tasks.append(task.to_dict())
                    
            return ProtocolMessage(
                message_type=MessageType.STATUS,
                data={"tasks": tasks},
                context_id=context_id
            )
            
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
        
    def get_tasks_by_context(self, context_id: str) -> List[Task]:
        """Get all tasks for a context."""
        return [
            task for task in self._tasks.values()
            if task.context_id == context_id
        ]
        
    def cleanup_completed_tasks(self, max_age_seconds: int = 3600):
        """Clean up old completed tasks.
        
        Args:
            max_age_seconds: Maximum age for completed tasks
        """
        now = datetime.now()
        to_remove = []
        
        for task_id, task in self._tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                age = (now - task.updated_at).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(task_id)
                    
        for task_id in to_remove:
            del self._tasks[task_id]
            
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old tasks")