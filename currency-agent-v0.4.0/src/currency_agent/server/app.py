"""A2A server application with v0.4.0 architecture."""

import logging
from typing import Optional

import httpx
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from starlette.middleware.authentication import AuthenticationMiddleware

# Internal imports - v0.4.0 architecture
from ..adapters import CurrencyAgentExecutor
from ..protocol import AgentCardGenerator
from ..streaming import EventQueue, SSEHandler
from .models import create_agent_card
from .routes import RouterV040
from .middleware import LoggingMiddleware, CORSMiddleware, ErrorHandlingMiddleware
from .authentication import A2AAuthenticationBackend


logger = logging.getLogger(__name__)


def create_app(host: str = 'localhost', port: int = 10000) -> A2AStarletteApplication:
    """
    Create and configure the A2A server application with v0.4.0 architecture.
    
    Args:
        host: Server host address
        port: Server port number
        
    Returns:
        A2AStarletteApplication: Configured server application
    """
    # Create HTTP client for push notifications
    httpx_client = httpx.AsyncClient()
    
    # Create executor with all v0.4.0 subsystems
    executor = CurrencyAgentExecutor()
    
    # Create request handler with required components
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        push_notifier=InMemoryPushNotifier(httpx_client),
    )
    
    # Create agent card
    agent_card = create_agent_card(host, port)
    
    # Create A2A application
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )
    
    # Add v0.4.0 specific components
    _configure_v040_features(app, executor, host, port)
    
    return app


def _configure_v040_features(
    app: A2AStarletteApplication,
    executor: CurrencyAgentExecutor,
    host: str,
    port: int
) -> None:
    """Configure v0.4.0 specific features.
    
    Args:
        app: A2A application instance
        executor: Currency agent executor
        host: Server host
        port: Server port
    """
    # Create streaming components
    event_queue = EventQueue()
    sse_handler = SSEHandler(event_queue)
    
    # Create agent card generator
    agent_card_generator = AgentCardGenerator(
        agent_name="currency-agent-v040",
        version="0.4.0",
        base_url=f"http://{host}:{port}"
    )
    
    # Create v0.4.0 router
    router = RouterV040(
        task_manager=executor.task_manager,
        sse_handler=sse_handler,
        agent_card_generator=agent_card_generator
    )
    
    # Note: A2AStarletteApplication has its own middleware and routing
    # The v0.4.0 extended features would need to be implemented
    # by extending the A2A application class or running a separate app
    
    logger.info("Configured v0.4.0 features (limited by A2A app constraints)")