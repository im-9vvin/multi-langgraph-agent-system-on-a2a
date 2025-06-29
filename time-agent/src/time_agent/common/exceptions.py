"""Custom exceptions for time agent."""


class TimeAgentError(Exception):
    """Base exception for time agent."""
    pass


class ConfigurationError(TimeAgentError):
    """Configuration related errors."""
    pass


class ProtocolError(TimeAgentError):
    """A2A protocol related errors."""
    pass


class AgentExecutionError(TimeAgentError):
    """Agent execution errors."""
    pass


class TimeOperationError(TimeAgentError):
    """Time operation specific errors."""
    pass


class CheckpointError(TimeAgentError):
    """Checkpointing related errors."""
    pass


class StreamingError(TimeAgentError):
    """Streaming related errors."""
    pass