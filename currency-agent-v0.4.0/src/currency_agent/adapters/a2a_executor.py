"""A2A Protocol executor with full v0.4.0 architecture support."""

import logging
import asyncio
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
    UnsupportedOperationError,
)
from a2a.utils import new_task, new_agent_text_message
from a2a.utils.errors import ServerError

# Internal imports - v0.4.0 architecture
from ..core.agent import CurrencyAgent
from ..protocol import TaskManager, MessageHandler, ProtocolValidator
from ..protocol.models import TaskStatus, A2ATask
from ..streaming import EventQueue as StreamEventQueue, StreamConverter
from ..checkpointing import A2ACheckpointer, StateSynchronizer, MemoryBackend
from .langgraph_wrapper import LangGraphWrapper
from .state_translator import StateTranslator


logger = logging.getLogger(__name__)


class CurrencyAgentExecutor(AgentExecutor):
    """
    A2A Protocol executor for Currency Agent with v0.4.0 architecture.
    
    This executor orchestrates all subsystems:
    - Protocol handling via dedicated subsystem
    - Streaming via SSE subsystem
    - Checkpointing for state persistence
    - LangGraph integration via wrappers
    """
    
    def __init__(self):
        """Initialize executor with all v0.4.0 subsystems."""
        # Core agent
        self.agent = CurrencyAgent()
        
        # Protocol subsystem
        self.task_manager = TaskManager()
        self.message_handler = MessageHandler()
        self.validator = ProtocolValidator()
        
        # Streaming subsystem
        self.stream_event_queue = StreamEventQueue()
        self.stream_converter = StreamConverter(self.stream_event_queue)
        
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
        
        # Streaming subsystem will be started when needed
        self._stream_started = False
        
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
        # Start streaming subsystem if not started
        if not self._stream_started:
            await self.stream_event_queue.start()
            self._stream_started = True
            
        # Validate request using protocol subsystem
        query = context.get_user_input()
        is_valid, error = self.validator.validate_task_input({"query": query})
        if not is_valid:
            raise ServerError(error=InvalidParamsError(message=error))
        
        # Get or create A2A SDK task
        sdk_task = context.current_task
        if not sdk_task:
            sdk_task = new_task(context.message)
            await event_queue.enqueue_event(sdk_task)
        
        # Create internal task via task manager
        internal_task = await self.task_manager.create_task(
            task_id=sdk_task.id,
            input_data={"query": query},
            metadata={
                "context_id": sdk_task.contextId
            }
        )
        
        # Create task updater for A2A SDK
        updater = TaskUpdater(event_queue, sdk_task.id, sdk_task.contextId)
        
        # Initialize checkpoint_task
        checkpoint_task = None
        
        try:
            # Update task status to processing
            await self.task_manager.update_task_status(
                sdk_task.id,
                TaskStatus.PROCESSING
            )
            await updater.update_status(TaskState.working)
            
            # Setup auto-checkpointing if enabled
            if self.state_synchronizer.auto_checkpoint:
                checkpoint_task = await self.state_synchronizer.setup_auto_sync(
                    sdk_task.id,
                    interval=30
                )
            else:
                checkpoint_task = None
                
            # Process with LangGraph directly (simpler approach)
            # We'll still use the wrapper for checkpointing but handle events directly
            async for item in self.agent.stream(query, sdk_task.contextId):
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']
                content = item['content']
                
                # Handle working state
                if not is_task_complete and not require_user_input:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            content,
                            sdk_task.contextId,
                            sdk_task.id,
                        ),
                    )
                
                # Handle input required state
                elif require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            content,
                            sdk_task.contextId,
                            sdk_task.id,
                        ),
                        final=True,
                    )
                    break
                
                # Handle completion state
                else:
                    # Add result as artifact
                    await updater.add_artifact(
                        [Part(root=TextPart(text=content))],
                        name='conversion_result',
                    )
                    # Mark task as complete
                    await updater.complete()
                    break
            
            # Final checkpoint
            await self.state_synchronizer.sync_task_to_checkpoint(sdk_task.id)
            
            # Update task status to completed
            await self.task_manager.update_task_status(
                sdk_task.id,
                TaskStatus.COMPLETED
            )
            
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
            # Cleanup
            if checkpoint_task:
                checkpoint_task.cancel()
            self.stream_event_queue.remove_queue(sdk_task.id)
                
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """
        Cancel a running task with proper cleanup.
        
        Args:
            context: Context of the task to cancel
            event_queue: Event queue for notifications
        """
        task_id = context.current_task.id if context.current_task else None
        if not task_id:
            raise ServerError(error=InvalidParamsError(message="No task to cancel"))
            
        try:
            # Update task status
            await self.task_manager.update_task_status(
                task_id,
                TaskStatus.CANCELLED
            )
            
            # Cancel streaming
            self.stream_event_queue.remove_queue(task_id)
            
            # Notify via A2A
            updater = TaskUpdater(event_queue, task_id, context.current_task.contextId)
            await updater.update_status(TaskState.cancelled)
            
        except Exception as e:
            logger.error(f"Cancel error for task {task_id}: {e}")
            raise ServerError(error=InternalError(message=str(e))) from e