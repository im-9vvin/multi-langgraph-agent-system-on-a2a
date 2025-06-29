"""Stream converter adapter for bridging subsystems."""

import logging
from typing import Any, AsyncGenerator, Dict, Optional

from ..streaming.event_queue import EventQueue
from ..streaming.stream_converter import StreamConverter as BaseStreamConverter

logger = logging.getLogger(__name__)


class StreamConverterAdapter:
    """Adapter for stream conversion between subsystems."""
    
    def __init__(self, event_queue: Optional[EventQueue] = None):
        """Initialize stream converter adapter.
        
        Args:
            event_queue: Optional shared event queue
        """
        self.event_queue = event_queue or EventQueue()
        self.base_converter = BaseStreamConverter()
    
    async def convert_and_queue(
        self,
        agent_stream: AsyncGenerator[Any, None],
        task_id: str
    ):
        """Convert agent stream and queue events.
        
        Args:
            agent_stream: Raw agent stream
            task_id: Associated task ID
        """
        try:
            async for event in self.base_converter.convert_agent_stream(agent_stream):
                # Add task ID to event
                event["task_id"] = task_id
                
                # Queue the event
                await self.event_queue.put(event)
                
        except Exception as e:
            logger.error(f"Stream conversion error for task {task_id}: {e}")
            
            # Queue error event
            error_event = {
                "type": "error",
                "task_id": task_id,
                "data": {"error": str(e)}
            }
            await self.event_queue.put(error_event)
    
    async def bridge_to_a2a(
        self,
        agent_stream: AsyncGenerator[Any, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Bridge LangGraph stream to A2A compatible format.
        
        Args:
            agent_stream: Raw agent stream
            
        Yields:
            A2A compatible events
        """
        async for event in self.base_converter.convert_agent_stream(agent_stream):
            # Transform to A2A format
            if event["type"] == "ai_message":
                yield {
                    "type": "agent_response",
                    "content": event["data"].get("content", ""),
                    "tool_calls": event["data"].get("tool_calls", [])
                }
            
            elif event["type"] == "tool_call":
                yield {
                    "type": "tool_invocation",
                    "tools": event["data"]
                }
            
            elif event["type"] == "stream_end":
                yield {
                    "type": "task_complete",
                    "final": True
                }
            
            else:
                # Pass through other events
                yield event