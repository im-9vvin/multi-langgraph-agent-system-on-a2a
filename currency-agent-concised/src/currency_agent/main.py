# Standard library imports
import logging
import os
import sys

# Third-party imports
import click
import uvicorn

# Internal imports
from .common.config import config
from .common.exceptions import MissingAPIKeyError
from .common.logging import setup_logging
from .server.app import create_app


# Get logger
logger = logging.getLogger(__name__)


@click.command()
@click.option('--host', 'host', default='localhost', help='Server host address')
@click.option('--port', 'port', default=10000, type=int, help='Server port number')
@click.option('--log-level', 'log_level', default='INFO', help='Logging level')
def main(host: str, port: int, log_level: str) -> None:
    """
    Start the Currency Agent server.
    
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
        # Validate configuration
        config.validate()
        
        # Set OpenAI API key if using OpenAI
        if config.model_source == 'openai' and config.api_key:
            os.environ["OPENAI_API_KEY"] = config.api_key
        
        # Create A2A application
        logger.info(f"Starting Currency Agent server on {host}:{port}")
        server = create_app(host, port)
        
        # Run the server
        uvicorn.run(server.build(), host=host, port=port)
        
    except MissingAPIKeyError as e:
        logger.error(f'Configuration Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()