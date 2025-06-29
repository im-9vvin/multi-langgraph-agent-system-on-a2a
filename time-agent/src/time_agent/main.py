"""Main entry point for time agent."""

import asyncio
import logging
import os

import click
import uvicorn
from dotenv import load_dotenv

from .common.config import settings
from .common.logging import setup_logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--host",
    default=settings.host,
    help="Host to bind to",
    show_default=True
)
@click.option(
    "--port",
    default=settings.port,
    type=int,
    help="Port to bind to",
    show_default=True
)
@click.option(
    "--log-level",
    default=settings.log_level,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Logging level",
    show_default=True
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development"
)
def main(host: str, port: int, log_level: str, reload: bool):
    """Run the Time Agent server."""
    # Setup logging
    setup_logging(level=log_level)
    
    logger.info(f"Starting Time Agent v1.0.0")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Model: {settings.model_name}")
    logger.info(f"Local timezone: {settings.local_timezone}")
    
    # Create the app directly instead of using string import
    from .server.app import create_app
    app = create_app(host=host, port=port)
    
    # Run server - app is already built ASGI app from create_app
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level.lower(),
        access_log=log_level == "DEBUG"
    )


if __name__ == "__main__":
    main()