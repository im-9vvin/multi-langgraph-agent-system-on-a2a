"""Configuration management for time agent."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    openai_api_key: str = Field(
        default="",
        env="OPENAI_API_KEY",
        description="OpenAI API key for LLM"
    )
    
    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Server host"
    )
    port: int = Field(
        default=8002,
        env="PORT",
        description="Server port"
    )
    
    # Agent Configuration
    model_name: str = Field(
        default="gpt-4o-mini",
        env="MODEL_NAME",
        description="OpenAI model to use"
    )
    temperature: float = Field(
        default=0.0,
        env="TEMPERATURE",
        description="Model temperature"
    )
    local_timezone: str = Field(
        default="UTC",
        env="LOCAL_TIMEZONE",
        description="Default local timezone"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    
    # Features
    enable_streaming: bool = Field(
        default=True,
        env="ENABLE_STREAMING",
        description="Enable SSE streaming"
    )
    enable_checkpointing: bool = Field(
        default=True,
        env="ENABLE_CHECKPOINTING",
        description="Enable state checkpointing"
    )
    
    # Limits
    max_concurrent_tasks: int = Field(
        default=10,
        env="MAX_CONCURRENT_TASKS",
        description="Maximum concurrent tasks"
    )
    task_timeout: int = Field(
        default=300,
        env="TASK_TIMEOUT",
        description="Task timeout in seconds"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()