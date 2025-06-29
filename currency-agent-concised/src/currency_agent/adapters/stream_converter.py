# Standard library imports
from collections.abc import AsyncIterable
from typing import Any, Dict

# A2A protocol imports
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, Task, TaskState, TextPart
from a2a.utils import new_agent_text_message


class StreamConverter:
    """
    Converts LangGraph streaming responses to A2A protocol events.
    
    This class handles the translation between LangGraph's streaming
    format and A2A's event-based protocol, ensuring proper task
    state management and message formatting.
    """
    
    async def convert_stream(
        self,
        agent_stream: AsyncIterable[Dict[str, Any]],
        task: Task,
        updater: TaskUpdater
    ) -> AsyncIterable[None]:
        """
        Convert agent stream to A2A events.
        
        Args:
            agent_stream: Stream of responses from the LangGraph agent
            task: Current A2A task
            updater: Task updater for sending status updates
            
        Yields:
            None (events are sent through the updater)
        """
        async for item in agent_stream:
            is_task_complete = item['is_task_complete']
            require_user_input = item['require_user_input']
            content = item['content']
            
            # Handle working state
            if not is_task_complete and not require_user_input:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        content,
                        task.contextId,
                        task.id,
                    ),
                )
            
            # Handle input required state
            elif require_user_input:
                await updater.update_status(
                    TaskState.input_required,
                    new_agent_text_message(
                        content,
                        task.contextId,
                        task.id,
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
            
            yield  # Yield control back to event loop