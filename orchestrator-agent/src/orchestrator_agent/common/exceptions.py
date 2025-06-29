"""Custom exceptions for the orchestrator agent."""


class OrchestratorError(Exception):
    """Base exception for orchestrator agent errors."""

    pass


class RemoteAgentError(OrchestratorError):
    """Error communicating with remote agent."""

    def __init__(self, agent_url: str, message: str):
        self.agent_url = agent_url
        super().__init__(f"Error with agent {agent_url}: {message}")


class ProtocolError(OrchestratorError):
    """A2A protocol violation error."""

    pass


class RoutingError(OrchestratorError):
    """Error routing request to appropriate agent."""

    pass


class TaskError(OrchestratorError):
    """Task execution error."""

    pass


class CheckpointError(OrchestratorError):
    """Checkpointing error."""

    pass