"""Configuration management for the orchestrator agent."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration for the orchestrator agent."""

    # LLM Provider
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", env="LLM_MODEL")

    # A2A Server Configuration
    a2a_host: str = Field(default="localhost", env="A2A_HOST")
    a2a_port: int = Field(default=10002, env="A2A_PORT")

    # Remote Agent Endpoints
    agent_1_url: str = Field(default="http://localhost:10000", env="AGENT_1_URL")
    agent_2_url: str = Field(default="http://localhost:10001", env="AGENT_2_URL")
    agent_3_url: Optional[str] = Field(default=None, env="AGENT_3_URL")
    agent_3_api_key: Optional[str] = Field(default=None, env="AGENT_3_API_KEY")
    agent_4_url: Optional[str] = Field(default=None, env="AGENT_4_URL")
    agent_5_url: Optional[str] = Field(default=None, env="AGENT_5_URL")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Checkpointing
    checkpoint_interval: int = Field(default=30, env="CHECKPOINT_INTERVAL")
    checkpoint_backend: str = Field(default="memory", env="CHECKPOINT_BACKEND")

    # Performance
    max_concurrent_tasks: int = Field(default=100, env="MAX_CONCURRENT_TASKS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    stream_timeout: int = Field(default=300, env="STREAM_TIMEOUT")

    # SSE Configuration
    sse_retry_timeout: int = Field(default=3000, env="SSE_RETRY_TIMEOUT")
    sse_ping_interval: int = Field(default=30, env="SSE_PING_INTERVAL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_llm_api_key(self) -> str:
        """Get the configured LLM API key."""
        if self.openai_api_key:
            return self.openai_api_key
        elif self.google_api_key:
            return self.google_api_key
        else:
            raise ValueError("No LLM API key configured. Set OPENAI_API_KEY or GOOGLE_API_KEY.")

    def get_remote_agents(self) -> list[str]:
        """Get the list of remote agent URLs."""
        agents = [self.agent_1_url, self.agent_2_url]
        
        # Add optional agents if configured
        if self.agent_3_url:
            agents.append(self.agent_3_url)
        if self.agent_4_url:
            agents.append(self.agent_4_url)
        if self.agent_5_url:
            agents.append(self.agent_5_url)
            
        return agents


def load_config() -> Config:
    """Load configuration from environment."""
    # Load .env file - dotenv will automatically find it
    load_dotenv()

    try:
        return Config()
    except ValidationError as e:
        raise ValueError(f"Invalid configuration: {e}") from e


# Global configuration instance
config = load_config()