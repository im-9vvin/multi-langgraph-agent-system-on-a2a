"""Generate agent card for the orchestrator."""

from ..common.config import config
from .models import AgentCard


def generate_agent_card() -> AgentCard:
    """Generate the agent card for discovery."""
    return AgentCard(
        name="orchestrator-agent-v040",
        version="0.4.0",
        description="A2A Orchestrator Agent that coordinates tasks across multiple specialized agents",
        capabilities=[
            "multi_agent_orchestration",
            "task_decomposition",
            "parallel_execution",
            "result_aggregation",
            "error_handling",
            "streaming_responses",
            "task_checkpointing"
        ],
        endpoints={
            "message": "/message",
            "stream": "/message/stream",
            "tasks": "/tasks",
            "health": "/health"
        },
        orchestration={
            "remote_agents": config.get_remote_agents(),
            "max_concurrent_tasks": config.max_concurrent_tasks,
            "supports_parallel": True,
            "supports_streaming": True
        }
    )