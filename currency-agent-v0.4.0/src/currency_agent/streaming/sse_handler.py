"""Server-Sent Events handler for A2A streaming."""

import asyncio
import json
import logging
from typing import AsyncIterator, Optional, Dict, Any
from datetime import datetime

from starlette.responses import StreamingResponse
from starlette.requests import Request

from .formatters import SSEFormatter
from .event_queue import EventQueue
from ..protocol.models import TaskYieldUpdate


logger = logging.getLogger(__name__)


class SSEHandler:
    """Manages Server-Sent Events for A2A protocol."""
    
    def __init__(self, 
                 event_queue: EventQueue,
                 heartbeat_interval: int = 30,
                 reconnect_time: int = 5000):
        """Initialize SSE handler.
        
        Args:
            event_queue: Event queue instance
            heartbeat_interval: Heartbeat interval in seconds
            reconnect_time: Client reconnect time in milliseconds
        """
        self.event_queue = event_queue
        self.formatter = SSEFormatter()
        self.heartbeat_interval = heartbeat_interval
        self.reconnect_time = reconnect_time
        self._active_connections: Dict[str, asyncio.Task] = {}
        
    async def create_sse_response(self, 
                                 request: Request,
                                 task_id: str) -> StreamingResponse:
        """Create SSE streaming response for a task.
        
        Args:
            request: Starlette request
            task_id: Task ID to stream events for
            
        Returns:
            StreamingResponse configured for SSE
        """
        # Check for Last-Event-ID header for reconnection
        last_event_id = request.headers.get('Last-Event-ID')
        if last_event_id:
            logger.info(f"Client reconnecting from event: {last_event_id}")
            
        # Create event generator
        generator = self._create_event_generator(task_id, last_event_id)
        
        # Create streaming response
        return StreamingResponse(
            generator,
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',  # Disable Nginx buffering
            }
        )
    
    async def _create_event_generator(self,
                                     task_id: str,
                                     last_event_id: Optional[str] = None) -> AsyncIterator[str]:
        """Create SSE event generator for a task.
        
        Args:
            task_id: Task ID to stream events for
            last_event_id: Last event ID for reconnection
            
        Yields:
            SSE formatted events
        """
        try:
            # Send initial retry configuration
            yield self.formatter.format_retry(self.reconnect_time)
            
            # Send any missed events if reconnecting
            if last_event_id:
                async for event in self._get_missed_events(task_id, last_event_id):
                    yield event
                    
            # Stream new events
            event_sequence = 0
            heartbeat_task = asyncio.create_task(self._heartbeat_generator())
            
            try:
                while True:
                    # Wait for either an event or heartbeat
                    done, pending = await asyncio.wait(
                        [
                            asyncio.create_task(self.event_queue.get_event(task_id)),
                            asyncio.create_task(heartbeat_task.__anext__())
                        ],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()
                        
                    # Process completed task
                    for task in done:
                        try:
                            result = task.result()
                            
                            if isinstance(result, dict):  # Event from queue
                                event_sequence += 1
                                event_id = f"{task_id}:{event_sequence}"
                                yield self.formatter.format_event(
                                    data=result,
                                    event=result.get('event_type', 'message'),
                                    id=event_id
                                )
                                
                                # Check for terminal events
                                if result.get('event_type') in ['completed', 'failed']:
                                    logger.info(f"Task {task_id} reached terminal state")
                                    return
                                    
                            else:  # Heartbeat
                                yield self.formatter.format_comment("heartbeat")
                                
                        except Exception as e:
                            logger.error(f"Error processing event: {e}")
                            
            finally:
                heartbeat_task.cancel()
                
        except asyncio.CancelledError:
            logger.info(f"SSE connection closed for task: {task_id}")
            raise
        except Exception as e:
            logger.error(f"SSE generator error: {e}")
            yield self.formatter.format_event(
                data={"error": str(e)},
                event="error"
            )
            
    async def _heartbeat_generator(self) -> AsyncIterator[str]:
        """Generate heartbeat events.
        
        Yields:
            Heartbeat markers
        """
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            yield "heartbeat"
            
    async def _get_missed_events(self, 
                                task_id: str,
                                last_event_id: str) -> AsyncIterator[str]:
        """Retrieve events missed during disconnection.
        
        Args:
            task_id: Task ID
            last_event_id: Last received event ID
            
        Yields:
            Missed events in SSE format
        """
        # Extract sequence number from event ID
        try:
            _, last_sequence = last_event_id.split(':')
            last_sequence = int(last_sequence)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid last event ID: {last_event_id}")
            return
            
        # Get missed events from queue history
        missed_events = await self.event_queue.get_events_since(task_id, last_sequence)
        
        for seq, event in enumerate(missed_events, start=last_sequence + 1):
            event_id = f"{task_id}:{seq}"
            yield self.formatter.format_event(
                data=event,
                event=event.get('event_type', 'message'),
                id=event_id
            )
    
    def close_connection(self, task_id: str) -> None:
        """Close SSE connection for a task.
        
        Args:
            task_id: Task ID
        """
        if task_id in self._active_connections:
            self._active_connections[task_id].cancel()
            del self._active_connections[task_id]
            logger.info(f"Closed SSE connection for task: {task_id}")