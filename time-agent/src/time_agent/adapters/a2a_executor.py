"""A2A Protocol executor with full v0.4.0 architecture support."""

import logging
from typing import Optional

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
)
from a2a.utils import new_task, new_agent_text_message
from a2a.utils.errors import ServerError

# Internal imports - v0.4.0 architecture
from ..core.agent import TimeAgent
from ..protocol import TaskManager, MessageHandler, ProtocolValidator
from ..protocol.models import TaskStatus
from ..streaming import EventQueue as StreamEventQueue, StreamConverter
from ..checkpointing import A2ACheckpointer, StateSynchronizer, MemoryBackend
from .langgraph_wrapper import LangGraphWrapper
from .state_translator import StateTranslator

logger = logging.getLogger(__name__)


class TimeAgentExecutor(AgentExecutor):
    """
    A2A Protocol executor for Time Agent with v0.4.0 architecture.
    
    This executor orchestrates all subsystems:
    - Protocol handling via dedicated subsystem
    - Streaming via SSE subsystem
    - Checkpointing for state persistence
    - LangGraph integration via wrappers
    """
    
    def __init__(self):
        """Initialize executor with all v0.4.0 subsystems."""
        # Core agent
        self.agent = TimeAgent()
        
        # Protocol subsystem
        self.task_manager = TaskManager()
        self.message_handler = MessageHandler()
        self.validator = ProtocolValidator()
        
        # Streaming subsystem
        self.stream_event_queue = StreamEventQueue()
        self.stream_converter = StreamConverter()
        
        # Checkpointing subsystem
        self.storage_backend = MemoryBackend()
        self.checkpointer = A2ACheckpointer(self.storage_backend)
        self.state_synchronizer = StateSynchronizer(
            self.task_manager,
            self.checkpointer
        )
        
        # Adapters
        self.langgraph_wrapper = LangGraphWrapper(self.agent, self.checkpointer)
        self.state_translator = StateTranslator()
        
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute an A2A request using v0.4.0 architecture.
        
        Args:
            context: Request context containing user input and task info
            event_queue: A2A event queue for sending events to client
        """
        # Get or create A2A SDK task
        sdk_task = context.current_task
        if not sdk_task:
            sdk_task = new_task(context.message)
            await event_queue.enqueue_event(sdk_task)
        
        # Extract messages from context
        messages = []
        
        # Try to get user input directly
        user_input = context.get_user_input()
        if user_input:
            messages = [{"role": "user", "content": user_input}]
        
        # Validate messages
        if not messages:
            raise ServerError(error=InvalidParamsError(message="No messages provided"))
        
        # Create internal task via task manager
        internal_task = await self.task_manager.create_task(
            task_id=sdk_task.id,
            input_data={"messages": messages}
        )
        
        # Create task updater for A2A SDK
        updater = TaskUpdater(event_queue, sdk_task.id, sdk_task.contextId)
        
        try:
            # Update task status to processing
            await self.task_manager.update_task_status(
                sdk_task.id,
                TaskStatus.PROCESSING
            )
            await updater.update_status(TaskState.working)
            
            # Process with agent through wrapper
            result = await self.langgraph_wrapper.execute(
                messages=messages,
                thread_id=sdk_task.id
            )
            
            if result["success"]:
                # Extract response
                response_text = result["response"]
                
                # Add result as artifact
                await updater.add_artifact(
                    [Part(root=TextPart(text=response_text))],
                    name='time_response',
                )
                
                # Mark task as complete
                await updater.complete()
                
                # Update internal task
                await self.task_manager.update_task_status(
                    sdk_task.id,
                    TaskStatus.COMPLETED,
                    output_data=result
                )
            else:
                # Handle error
                error_msg = result.get("error", "Unknown error")
                await self.task_manager.update_task_status(
                    sdk_task.id,
                    TaskStatus.FAILED,
                    error=error_msg
                )
                await updater.update_status(TaskState.failed)
                raise ServerError(error=InternalError(message=error_msg))
            
        except Exception as e:
            logger.error(f"Execution error for task {sdk_task.id}: {e}")
            
            # Update task status to failed
            await self.task_manager.update_task_status(
                sdk_task.id,
                TaskStatus.FAILED,
                error=str(e)
            )
            await updater.update_status(TaskState.failed)
            
            raise ServerError(error=InternalError(message=str(e))) from e
        
        finally:
            # Cleanup agent resources
            await self.agent.cleanup()
    
    async def cancel(self, task_id: str) -> None:
        """Cancel a running task.
        
        Args:
            task_id: Task ID to cancel
        """
        # Update task status to cancelled
        await self.task_manager.update_task_status(
            task_id,
            TaskStatus.CANCELLED
        )
        logger.info(f"Cancelled task {task_id}")