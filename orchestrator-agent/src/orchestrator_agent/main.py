"""Main entry point for the orchestrator agent."""

import logging
import os
import sys

import click
import uvicorn

from .common.config import config
from .common.logging import setup_logging
from .server.a2a_app import create_app


logger = logging.getLogger(__name__)


@click.command()
@click.option('--host', 'host', default='localhost', help='Server host address')
@click.option('--port', 'port', default=10002, type=int, help='Server port number')
@click.option('--log-level', 'log_level', default='INFO', help='Logging level')
def main(host: str, port: int, log_level: str) -> None:
    """
    Start the Orchestrator Agent server.
    
    This function initializes the agent, validates configuration,
    and starts the A2A-compliant server.
    
    Args:
        host: Server host address
        port: Server port number
        log_level: Logging level
    """
    # Setup logging
    setup_logging(log_level)
    
    try:
        # Set OpenAI API key from config
        if config.openai_api_key:
            os.environ["OPENAI_API_KEY"] = config.openai_api_key
        elif config.google_api_key:
            os.environ["GOOGLE_API_KEY"] = config.google_api_key
        else:
            raise ValueError("No LLM API key configured")
        
        # Create A2A application
        logger.info(f"Starting Orchestrator Agent server on {host}:{port}")
        server = create_app(host, port)
        
        # Run the server
        uvicorn.run(server.build(), host=host, port=port)
        
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == "__main__":
    main()