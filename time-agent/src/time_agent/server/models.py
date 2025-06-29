"""Server-specific models for API requests/responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """A2A message request model."""
    jsonrpc: str = "2.0"
    method: str = "message"
    params: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[str] = None


class TaskResponse(BaseModel):
    """Task creation response."""
    task: Dict[str, Any]


class TaskListResponse(BaseModel):
    """Task list response."""
    tasks: List[Dict[str, Any]]
    total: int
    page: int = 1
    limit: int = 10


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]
    metrics: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


def create_agent_card(host: str, port: int) -> AgentCard:
    """Create the A2A agent card for the time agent.
    
    Args:
        host: Server host address
        port: Server port number
        
    Returns:
        AgentCard: Configured agent card with metadata
    """
    # Define agent capabilities
    capabilities = AgentCapabilities(
        streaming=True,
        pushNotifications=True
    )
    
    # Define agent skills
    skills = [
        AgentSkill(
            id='get_current_time',
            name='Get Current Time',
            description='Get the current time in any timezone',
            tags=['time', 'timezone', 'current time'],
            examples=['What time is it in Tokyo?', 'Current time in New York'],
        ),
        AgentSkill(
            id='convert_time',
            name='Convert Time Between Timezones',
            description='Convert time from one timezone to another',
            tags=['time', 'timezone', 'conversion'],
            examples=['Convert 3:30 PM EST to London time', 'What is 14:00 Paris time in Singapore?'],
        )
    ]
    
    # Create and return agent card
    return AgentCard(
        name='Time Agent',
        description='Provides current time information and timezone conversions',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=capabilities,
        skills=skills,
    )