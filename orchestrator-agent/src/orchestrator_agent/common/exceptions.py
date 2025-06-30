"""Common exceptions for the orchestrator agent."""


class OrchestratorError(Exception):
    """Base exception for orchestrator agent errors."""
    pass


class ConfigurationError(OrchestratorError):
    """Raised when there is a configuration error."""
    pass


class AgentExecutionError(OrchestratorError):
    """Raised when agent execution fails."""
    pass


class RemoteAgentError(OrchestratorError):
    """Raised when a remote agent call fails."""
    pass