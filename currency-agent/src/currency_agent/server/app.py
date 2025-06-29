# Standard library imports
import logging

# Third-party imports
import httpx
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore

# Internal imports
from ..adapters.a2a_executor import CurrencyAgentExecutor
from .models import create_agent_card


# Configure logging
logger = logging.getLogger(__name__)


def create_app(host: str = 'localhost', port: int = 10000) -> A2AStarletteApplication:
    """
    Create and configure the A2A server application.
    
    Args:
        host: Server host address
        port: Server port number
        
    Returns:
        A2AStarletteApplication: Configured server application
    """
    # Create HTTP client for push notifications
    httpx_client = httpx.AsyncClient()
    
    # Create request handler with required components
    request_handler = DefaultRequestHandler(
        agent_executor=CurrencyAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_notifier=InMemoryPushNotifier(httpx_client),
    )
    
    # Create agent card
    agent_card = create_agent_card(host, port)
    
    # Create and return A2A application
    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )