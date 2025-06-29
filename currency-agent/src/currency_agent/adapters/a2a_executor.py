# Standard library imports
import logging

# A2A protocol imports
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

# Internal imports
from ..core.agent import CurrencyAgent
from .stream_converter import StreamConverter


# Configure logging
logger = logging.getLogger(__name__)


class CurrencyAgentExecutor(AgentExecutor):
    """
    A2A Protocol executor for the Currency Agent.
    
    This class bridges the A2A protocol with the LangGraph-based
    CurrencyAgent, handling request execution and response formatting.
    
    Key responsibilities:
    - Execute A2A requests using the CurrencyAgent
    - Convert agent responses to A2A events
    - Manage task state and lifecycle
    - Handle errors and exceptions
    """
    
    def __init__(self):
        """Initialize the executor with agent and converter."""
        self.agent = CurrencyAgent()
        self.stream_converter = StreamConverter()
    
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute an A2A request using the currency agent.
        
        Args:
            context: Request context containing user input and task info
            event_queue: Queue for sending events to the client
            
        Raises:
            ServerError: On validation failure or internal errors
        """
        # Validate the incoming request
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())
        
        # Extract user query
        query = context.get_user_input()
        
        # Get or create task
        task = context.current_task
        if not task:
            task = new_task(context.message)  # type: ignore
            await event_queue.enqueue_event(task)
        
        # Create task updater for status management
        updater = TaskUpdater(event_queue, task.id, task.contextId)
        
        try:
            # Process agent stream and convert to A2A events
            async for event in self.stream_converter.convert_stream(
                self.agent.stream(query, task.contextId),
                task,
                updater
            ):
                # Events are handled by the converter
                pass
                
        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            raise ServerError(error=InternalError()) from e
    
    def _validate_request(self, context: RequestContext) -> bool:
        """
        Validate the incoming request.
        
        Args:
            context: Request context to validate
            
        Returns:
            bool: True if there's an error, False if valid
        """
        # TODO: Add actual validation logic
        # e.g., check required fields, validate input format
        return False
    
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """
        Cancel a running task.
        
        Currently not supported for this agent.
        
        Args:
            context: Context of the task to cancel
            event_queue: Event queue for notifications
            
        Raises:
            ServerError: Always raises UnsupportedOperationError
        """
        raise ServerError(error=UnsupportedOperationError())