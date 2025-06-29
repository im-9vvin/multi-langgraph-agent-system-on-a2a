"""Event queue system for streaming."""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class EventQueue:
    """Manages event queuing and delivery for streaming."""
    
    def __init__(self, 
                 max_queue_size: int = 1000,
                 max_history_size: int = 100,
                 history_ttl: int = 3600):
        """Initialize event queue.
        
        Args:
            max_queue_size: Maximum events per queue
            max_history_size: Maximum historical events to keep
            history_ttl: History time-to-live in seconds
        """
        self.max_queue_size = max_queue_size
        self.max_history_size = max_history_size
        self.history_ttl = history_ttl
        
        # Task queues
        self._queues: Dict[str, asyncio.Queue] = {}
        
        # Event history for reconnection support
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self._history_timestamps: Dict[str, datetime] = {}
        
        # Cleanup task
        self._cleanup_task = None
        
    async def start(self) -> None:
        """Start the event queue system."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Event queue started")
        
    async def stop(self) -> None:
        """Stop the event queue system."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Event queue stopped")
        
    async def put_event(self, task_id: str, event: Dict[str, Any]) -> None:
        """Put an event in the queue.
        
        Args:
            task_id: Task ID
            event: Event data
            
        Raises:
            Exception: If queue is full
        """
        # Create queue if not exists
        if task_id not in self._queues:
            self._queues[task_id] = asyncio.Queue(maxsize=self.max_queue_size)
            
        # Add to queue
        try:
            await self._queues[task_id].put(event)
        except asyncio.QueueFull:
            logger.error(f"Queue full for task {task_id}, dropping event")
            raise Exception(f"Event queue full for task {task_id}")
            
        # Add to history
        self._history[task_id].append(event)
        self._history_timestamps[task_id] = datetime.utcnow()
        
    async def get_event(self, task_id: str) -> Dict[str, Any]:
        """Get an event from the queue.
        
        Args:
            task_id: Task ID
            
        Returns:
            Event data
        """
        # Create queue if not exists
        if task_id not in self._queues:
            self._queues[task_id] = asyncio.Queue(maxsize=self.max_queue_size)
            
        # Wait for event
        event = await self._queues[task_id].get()
        return event
        
    async def get_events_since(self, 
                             task_id: str,
                             sequence: int) -> List[Dict[str, Any]]:
        """Get events since a specific sequence number.
        
        Args:
            task_id: Task ID
            sequence: Last received sequence number
            
        Returns:
            List of missed events
        """
        if task_id not in self._history:
            return []
            
        # Find events with sequence > provided sequence
        missed_events = []
        for event in self._history[task_id]:
            if event.get('sequence', 0) > sequence:
                missed_events.append(event)
                
        return missed_events
        
    def get_queue_size(self, task_id: str) -> int:
        """Get current queue size for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Queue size
        """
        if task_id not in self._queues:
            return 0
        return self._queues[task_id].qsize()
        
    def remove_queue(self, task_id: str) -> None:
        """Remove queue for a task.
        
        Args:
            task_id: Task ID
        """
        if task_id in self._queues:
            del self._queues[task_id]
            
        if task_id in self._history:
            del self._history[task_id]
            
        if task_id in self._history_timestamps:
            del self._history_timestamps[task_id]
            
        logger.debug(f"Removed queue for task: {task_id}")
        
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of old queues and history."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                now = datetime.utcnow()
                cutoff = now - timedelta(seconds=self.history_ttl)
                
                # Find expired queues
                expired = []
                for task_id, timestamp in self._history_timestamps.items():
                    if timestamp < cutoff:
                        expired.append(task_id)
                        
                # Remove expired queues
                for task_id in expired:
                    self.remove_queue(task_id)
                    logger.info(f"Cleaned up expired queue: {task_id}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")