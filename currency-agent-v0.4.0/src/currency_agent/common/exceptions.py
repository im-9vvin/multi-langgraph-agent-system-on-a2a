# Custom exceptions for the Currency Agent


class CurrencyAgentError(Exception):
    """Base exception for all Currency Agent errors."""
    pass


class ConfigurationError(CurrencyAgentError):
    """Raised when there's a configuration error."""
    pass


class MissingAPIKeyError(ConfigurationError):
    """Raised when a required API key is missing."""
    pass


class AgentExecutionError(CurrencyAgentError):
    """Raised when there's an error during agent execution."""
    pass


class ProtocolError(CurrencyAgentError):
    """Raised when there's a protocol-related error."""
    pass


class TaskNotFoundError(CurrencyAgentError):
    """Raised when a task is not found."""
    pass


class InvalidTaskStateError(CurrencyAgentError):
    """Raised when an invalid task state transition is attempted."""
    pass