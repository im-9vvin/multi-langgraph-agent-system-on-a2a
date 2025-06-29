# Standard library imports
import os
from typing import Optional

# Third-party imports
from dotenv import load_dotenv


class Config:
    """
    Configuration management for the Currency Agent.
    
    Loads configuration from environment variables and provides
    centralized access to all configuration values.
    """
    
    def __init__(self):
        """Initialize configuration by loading environment variables."""
        load_dotenv()
    
    @property
    def model_source(self) -> str:
        """Get the model source (e.g., 'openai', 'google')."""
        return os.getenv('TOOL_MODEL_SRC', 'openai')
    
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return os.getenv('TOOL_MODEL_NAME', 'gpt-4o-mini')
    
    @property
    def model_temperature(self) -> float:
        """Get the model temperature."""
        return float(os.getenv('TOOL_MODEL_TEMPERATURE', '0'))
    
    @property
    def api_key(self) -> Optional[str]:
        """Get the API key for the model."""
        return os.getenv('TOOL_API_KEY')
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get the OpenAI API key."""
        return os.getenv('OPENAI_API_KEY')
    
    def validate(self) -> None:
        """
        Validate required configuration.
        
        Raises:
            ValueError: If required configuration is missing
        """
        if self.model_source == 'openai' and not self.api_key:
            raise ValueError(
                f'TOOL_API_KEY for "{self.model_source}" model environment variable not set.'
            )


# Global configuration instance
config = Config()