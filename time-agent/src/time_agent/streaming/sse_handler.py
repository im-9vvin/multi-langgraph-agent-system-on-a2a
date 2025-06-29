"""Server-Sent Events handler."""

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

from starlette.responses import StreamingResponse

from .event_queue import EventQueue
from .formatters import SSEFormatter

logger = logging.getLogger(__name__)


class SSEHandler:
    """Handles Server-Sent Events streaming."""
    
    def __init__(self, event_queue: Optional[EventQueue] = None):
        """Initialize SSE handler.
        
        Args:
            event_queue: Optional shared event queue
        """
        self.event_queue = event_queue or EventQueue()
        self.formatter = SSEFormatter()
    
    async def stream_events(
        self,
        client_id: Optional[str] = None,
        last_event_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream events to a client.
        
        Args:
            client_id: Optional client identifier
            last_event_id: Optional last received event ID for reconnection
            
        Yields:
            SSE-formatted events
        """
        logger.info(f"Starting SSE stream for client {client_id}")
        
        # Send initial comment to establish connection
        yield self.formatter.format_comment("connected")
        
        # If reconnecting, send missed events from history
        if last_event_id:
            # In a real implementation, you'd parse the last_event_id
            # to determine which events to replay
            logger.info(f"Client {client_id} reconnecting from event {last_event_id}")
        
        # Subscribe to events
        subscriber_queue = await self.event_queue.subscribe()
        
        try:
            while True:
                try:
                    # Wait for events with timeout for keep-alive
                    event = await asyncio.wait_for(
                        subscriber_queue.get(),
                        timeout=30.0
                    )
                    
                    # Format and yield event
                    if isinstance(event, dict) and "task_id" in event:
                        yield self.formatter.format_task_event(
                            task_id=event["task_id"],
                            event_type=event.get("type", "update"),
                            data=event.get("data", {})
                        )
                    else:
                        yield self.formatter.format_event(data=event)
                    
                except asyncio.TimeoutError:
                    # Send keep-alive comment
                    yield self.formatter.format_comment("keep-alive")
                    
                except Exception as e:
                    logger.error(f"Error streaming event: {e}")
                    yield self.formatter.format_event(
                        data={"error": str(e)},
                        event="error"
                    )
        
        finally:
            # Unsubscribe when done
            await self.event_queue.unsubscribe(subscriber_queue)
            logger.info(f"Ended SSE stream for client {client_id}")
    
    def create_response(
        self,
        client_id: Optional[str] = None,
        last_event_id: Optional[str] = None
    ) -> StreamingResponse:
        """Create a streaming response for SSE.
        
        Args:
            client_id: Optional client identifier
            last_event_id: Optional last event ID
            
        Returns:
            StreamingResponse configured for SSE
        """
        return StreamingResponse(
            self.stream_events(client_id, last_event_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    
    async def broadcast_event(self, event: Any):
        """Broadcast an event to all connected clients.
        
        Args:
            event: Event to broadcast
        """
        await self.event_queue.put(event)
    
    async def broadcast_task_update(
        self,
        task_id: str,
        event_type: str,
        data: dict[str, Any]
    ):
        """Broadcast a task update event.
        
        Args:
            task_id: Task ID
            event_type: Type of update
            data: Update data
        """
        event = {
            "task_id": task_id,
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_event(event)