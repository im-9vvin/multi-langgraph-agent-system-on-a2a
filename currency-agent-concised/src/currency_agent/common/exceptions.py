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