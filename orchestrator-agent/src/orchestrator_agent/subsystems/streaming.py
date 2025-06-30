"""Streaming subsystem for real-time updates."""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from collections import defaultdict

from ..common.exceptions import OrchestratorError
from ..common.logging import get_logger

logger = get_logger(__name__)


class StreamEvent:
    """Represents a stream event."""
    
    def __init__(self, event_type: str, data: Any, metadata: Optional[Dict] = None):
        """Initialize stream event.
        
        Args:
            event_type: Type of event
            data: Event data
            metadata: Optional event metadata
        """
        self.event_type = event_type
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.event_type,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
        
    def to_sse(self) -> str:
        """Convert to Server-Sent Events format."""
        event_dict = self.to_dict()
        return f"event: {self.event_type}\ndata: {json.dumps(event_dict)}\n\n"


class StreamingHandler:
    """Handles streaming for real-time updates."""
    
    def __init__(self):
        """Initialize streaming handler."""
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._event_history: Dict[str, List[StreamEvent]] = defaultdict(list)
        self._max_history_size = 100
        
    async def subscribe(self, stream_id: str, 
                       queue_size: int = 100) -> AsyncIterator[StreamEvent]:
        """Subscribe to a stream.
        
        Args:
            stream_id: ID of stream to subscribe to
            queue_size: Maximum queue size
            
        Yields:
            Stream events
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._subscribers[stream_id].append(queue)
        
        try:
            # Send historical events first
            for event in self._event_history.get(stream_id, []):
                yield event
                
            # Then stream new events
            while True:
                event = await queue.get()
                if event is None:  # Sentinel value to stop
                    break
                yield event
        finally:
            # Clean up subscription
            if queue in self._subscribers[stream_id]:
                self._subscribers[stream_id].remove(queue)
                
    async def publish(self, stream_id: str, event: StreamEvent):
        """Publish an event to a stream.
        
        Args:
            stream_id: ID of stream to publish to
            event: Event to publish
        """
        # Add to history
        history = self._event_history[stream_id]
        history.append(event)
        
        # Trim history if too large
        if len(history) > self._max_history_size:
            history.pop(0)
            
        # Publish to all subscribers
        dead_queues = []
        for queue in self._subscribers[stream_id]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"Queue full for stream {stream_id}, dropping event")
            except Exception as e:
                logger.error(f"Error publishing to queue: {e}")
                dead_queues.append(queue)
                
        # Remove dead queues
        for queue in dead_queues:
            self._subscribers[stream_id].remove(queue)
            
    async def close_stream(self, stream_id: str):
        """Close a stream and notify all subscribers.
        
        Args:
            stream_id: ID of stream to close
        """
        # Send sentinel value to all subscribers
        for queue in self._subscribers[stream_id]:
            try:
                queue.put_nowait(None)
            except Exception as e:
                logger.error(f"Error closing queue: {e}")
                
        # Clear subscribers and history
        del self._subscribers[stream_id]
        del self._event_history[stream_id]
        
    def create_sse_endpoint(self, stream_id: str) -> Callable:
        """Create an SSE endpoint for a stream.
        
        Args:
            stream_id: ID of stream
            
        Returns:
            Async generator for SSE endpoint
        """
        async def sse_generator():
            """Generate Server-Sent Events."""
            async for event in self.subscribe(stream_id):
                yield event.to_sse()
                
        return sse_generator
        
    async def publish_orchestration_event(self, context_id: str, 
                                        event_type: str, data: Any):
        """Publish an orchestration-specific event.
        
        Args:
            context_id: Context ID (used as stream ID)
            event_type: Type of orchestration event
            data: Event data
        """
        event = StreamEvent(
            event_type=f"orchestration.{event_type}",
            data=data,
            metadata={"context_id": context_id}
        )
        await self.publish(context_id, event)
        
    async def stream_langgraph_events(self, context_id: str, 
                                    langgraph_stream: AsyncIterator[Any]):
        """Stream events from LangGraph.
        
        Args:
            context_id: Context ID for the stream
            langgraph_stream: LangGraph event stream
        """
        try:
            async for chunk in langgraph_stream:
                # Parse LangGraph events
                if isinstance(chunk, dict):
                    for node, data in chunk.items():
                        await self.publish_orchestration_event(
                            context_id,
                            f"node.{node}",
                            data
                        )
                else:
                    # Raw data
                    await self.publish_orchestration_event(
                        context_id,
                        "data",
                        chunk
                    )
        except Exception as e:
            logger.error(f"Error streaming LangGraph events: {e}")
            await self.publish_orchestration_event(
                context_id,
                "error",
                {"error": str(e)}
            )
        finally:
            await self.publish_orchestration_event(
                context_id,
                "complete",
                {"status": "completed"}
            )