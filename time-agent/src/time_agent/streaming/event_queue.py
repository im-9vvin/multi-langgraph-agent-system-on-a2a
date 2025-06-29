"""Event queue management for streaming."""

import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Any, Deque, Optional

logger = logging.getLogger(__name__)


class EventQueue:
    """Manages event queuing with history for reconnection support."""
    
    def __init__(self, max_history: int = 100):
        """Initialize event queue.
        
        Args:
            max_history: Maximum number of events to keep in history
        """
        self._queue: asyncio.Queue = asyncio.Queue()
        self._history: Deque[tuple[datetime, Any]] = deque(maxlen=max_history)
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
    
    async def put(self, event: Any):
        """Add an event to the queue.
        
        Args:
            event: Event to add
        """
        timestamp = datetime.utcnow()
        
        async with self._lock:
            # Add to history
            self._history.append((timestamp, event))
            
            # Add to main queue
            await self._queue.put(event)
            
            # Notify all subscribers
            for subscriber in self._subscribers:
                try:
                    await subscriber.put(event)
                except asyncio.QueueFull:
                    logger.warning("Subscriber queue full, dropping event")
    
    async def get(self) -> Any:
        """Get the next event from the queue.
        
        Returns:
            Next event
        """
        return await self._queue.get()
    
    async def subscribe(self) -> asyncio.Queue:
        """Create a new subscriber queue.
        
        Returns:
            Subscriber queue
        """
        subscriber_queue = asyncio.Queue(maxsize=50)
        
        async with self._lock:
            self._subscribers.append(subscriber_queue)
        
        return subscriber_queue
    
    async def unsubscribe(self, queue: asyncio.Queue):
        """Remove a subscriber queue.
        
        Args:
            queue: Queue to remove
        """
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
    
    def get_history(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> list[Any]:
        """Get event history.
        
        Args:
            since: Optional timestamp to get events after
            limit: Optional maximum number of events
            
        Returns:
            List of historical events
        """
        events = []
        
        for timestamp, event in self._history:
            if since and timestamp <= since:
                continue
            
            events.append(event)
            
            if limit and len(events) >= limit:
                break
        
        return events
    
    def clear_history(self):
        """Clear event history."""
        self._history.clear()
    
    @property
    def history_size(self) -> int:
        """Get current history size."""
        return len(self._history)
    
    @property
    def subscriber_count(self) -> int:
        """Get current subscriber count."""
        return len(self._subscribers)