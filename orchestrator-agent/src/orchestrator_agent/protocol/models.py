"""Protocol models for A2A compliance."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class A2AMessage(BaseModel):
    """A2A protocol message."""
    
    messageId: str
    role: Literal["user", "assistant"]
    parts: list[dict[str, Any]]
    contextId: Optional[str] = None
    createdAt: Optional[datetime] = None


class TaskCreate(BaseModel):
    """Task creation request."""
    
    message: A2AMessage


class TaskStatus(BaseModel):
    """Task status response."""
    
    taskId: str
    contextId: str
    status: Literal["pending", "in_progress", "completed", "failed", "cancelled"]
    createdAt: datetime
    updatedAt: datetime
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentCard(BaseModel):
    """Agent card for discovery."""
    
    name: str
    version: str
    description: str
    capabilities: list[str]
    endpoints: dict[str, str]
    orchestration: dict[str, Any] = Field(default_factory=dict)