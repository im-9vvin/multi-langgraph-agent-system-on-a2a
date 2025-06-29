"""Main entry point for the orchestrator agent using A2A SDK."""

import click
import uvicorn

from .common import get_logger
from .common.config import config
from .server.app_v2 import create_app

logger = get_logger(__name__)


@click.command()
@click.option(
    "--host",
    default=config.a2a_host,
    help="Host to bind to"
)
@click.option(
    "--port",
    default=config.a2a_port,
    type=int,
    help="Port to bind to"
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development"
)
def main(host: str, port: int, reload: bool) -> None:
    """Run the orchestrator agent server."""
    logger.info(
        "Starting orchestrator agent",
        host=host,
        port=port,
        version="0.4.0"
    )
    
    # Log configured remote agents
    logger.info(
        "Configured remote agents",
        agents=config.get_remote_agents()
    )
    
    # Create app using A2A SDK
    app = create_app(host, port)
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=config.log_level.lower()
    )


if __name__ == "__main__":
    main()