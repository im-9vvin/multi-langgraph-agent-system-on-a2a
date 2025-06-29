"""FastAPI application setup for time agent server."""

import logging
import os
from dotenv import load_dotenv

import httpx
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route

from ..adapters.a2a_executor import TimeAgentExecutor
from ..common.config import settings
from ..common.logging import setup_logging
from .authentication import A2AAuthenticationBackend
from .middleware import ErrorHandlingMiddleware, LoggingMiddleware, MetricsMiddleware
from .models import create_agent_card
from .routes import TimeAgentRoutes

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def create_app(host: str = '0.0.0.0', port: int = 8002) -> Starlette:
    """Create and configure the A2A Starlette application.
    
    Args:
        host: Server host
        port: Server port
        
    Returns:
        Built ASGI app ready for uvicorn
    """
    # Setup logging
    setup_logging()
    
    # Create executor
    executor = TimeAgentExecutor()
    
    # Create A2A components
    task_store = InMemoryTaskStore()
    httpx_client = httpx.AsyncClient()
    push_notifier = InMemoryPushNotifier(httpx_client)
    
    # Create A2A request handler
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        push_notifier=push_notifier
    )
    
    # Create routes handler
    routes_handler = TimeAgentRoutes(request_handler, executor)
    
    # Create agent card
    agent_card = create_agent_card(host, port)
    
    # Create A2A app
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )
    
    # Note: A2AStarletteApplication has its own routing and middleware
    # It already includes the necessary endpoints for A2A protocol
    
    logger.info(f"Time Agent v1.0.0 configured for {host}:{port}")
    
    # Return the built ASGI app
    return a2a_app.build()


# Create app instance
app = create_app(host=settings.host, port=settings.port)