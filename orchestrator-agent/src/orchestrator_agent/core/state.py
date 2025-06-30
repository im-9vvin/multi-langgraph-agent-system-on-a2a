"""State definition for the orchestrator agent."""

from typing import Any, Literal, Optional, TypedDict

from langgraph.graph import MessagesState


class RemoteAgentCall(TypedDict):
    """Information about a remote agent call."""
    
    agent_url: str
    task_id: str
    status: Literal["pending", "in_progress", "completed", "failed"]
    result: Optional[Any]
    error: Optional[str]


class OrchestratorState(MessagesState):
    """State for the orchestrator agent."""
    
    # Current orchestration plan
    plan: Optional[str]
    
    # Remote agent routing decision
    routing_decision: Optional[dict[str, Any]]
    
    # Remote agent calls
    remote_calls: list[RemoteAgentCall]
    
    # Aggregated results
    aggregated_results: Optional[dict[str, Any]]
    
    # Current phase
    phase: Literal["planning", "routing", "executing", "aggregating", "complete"]
    
    # Error information
    error: Optional[str]
    
    # Context ID for conversation tracking
    context_id: Optional[str]