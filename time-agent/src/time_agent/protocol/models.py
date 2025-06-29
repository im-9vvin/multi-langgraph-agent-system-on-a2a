"""A2A Protocol models for type-safe message handling."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """A2A Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class A2AMessage(BaseModel):
    """A2A Protocol message model."""
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any]
    id: Optional[Union[str, int]] = None


class A2ATask(BaseModel):
    """A2A Task model with complete metadata."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override to handle datetime serialization."""
        data = super().model_dump(**kwargs)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data


class TaskYieldUpdate(BaseModel):
    """Streaming update event for A2A tasks."""
    task_id: str
    event_type: str = "yield"
    data: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TimeRequest(BaseModel):
    """Specific request model for time operations."""
    operation: str = Field(..., description="Operation type: 'current_time' or 'convert_time'")
    timezone: Optional[str] = Field(None, description="Target timezone for current_time")
    source_timezone: Optional[str] = Field(None, description="Source timezone for conversion")
    target_timezone: Optional[str] = Field(None, description="Target timezone for conversion")
    time: Optional[str] = Field(None, description="Time to convert in HH:MM format")


class TimeResponse(BaseModel):
    """Response model for time operations."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)