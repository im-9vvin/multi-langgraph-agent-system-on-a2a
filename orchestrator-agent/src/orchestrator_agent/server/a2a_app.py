"""A2A server application for orchestrator agent."""

import logging
import httpx
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore

from ..adapters import OrchestratorExecutor
from .models import create_agent_card
from .streaming_endpoints import add_streaming_endpoints
from .streaming_handler import StreamingRequestHandler


logger = logging.getLogger(__name__)


def create_app(host: str = 'localhost', port: int = 10002) -> A2AStarletteApplication:
    """
    Create and configure the A2A server application for orchestrator.
    
    Args:
        host: Server host address
        port: Server port number
        
    Returns:
        A2AStarletteApplication: Configured server application
    """
    # Create HTTP client for push notifications
    httpx_client = httpx.AsyncClient()
    
    # Create executor
    executor = OrchestratorExecutor()
    
    # Create streaming request handler
    request_handler = StreamingRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        push_notifier=InMemoryPushNotifier(httpx_client),
    )
    
    # Create agent card with streaming capability
    agent_card = create_agent_card(host, port)
    
    # Create A2A application
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )
    
    # TODO: Add streaming endpoints after A2A SDK supports custom routes
    # add_streaming_endpoints(app, executor)
    
    logger.info(f"Created A2A orchestrator server on {host}:{port}")
    
    return app