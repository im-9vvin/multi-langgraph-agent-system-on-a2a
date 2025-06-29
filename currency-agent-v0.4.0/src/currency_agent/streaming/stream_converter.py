"""Converter for LangGraph streams to A2A SSE events."""

import asyncio
import json
import logging
from typing import AsyncIterator, Any, Dict, Optional, List
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from ..protocol.models import TaskYieldUpdate
from .event_queue import EventQueue


logger = logging.getLogger(__name__)


class StreamConverter:
    """Converts LangGraph async streams to A2A SSE events."""
    
    def __init__(self, event_queue: EventQueue, batch_size: int = 10):
        """Initialize stream converter.
        
        Args:
            event_queue: Event queue for buffering
            batch_size: Token batch size for streaming
        """
        self.event_queue = event_queue
        self.batch_size = batch_size
        self._token_buffer: Dict[str, List[str]] = {}
        
    async def convert_stream(self,
                           task_id: str,
                           stream: AsyncIterator[Any]) -> None:
        """Convert LangGraph stream to A2A events.
        
        Args:
            task_id: Task ID
            stream: LangGraph async stream
        """
        try:
            sequence = 0
            self._token_buffer[task_id] = []
            
            async for event in stream:
                sequence += 1
                
                # Convert event based on type
                if isinstance(event, dict):
                    # Handle CurrencyAgent format
                    if 'is_task_complete' in event and 'content' in event:
                        await self._handle_currency_agent_event(task_id, event, sequence)
                    # Handle different event types
                    elif 'messages' in event:
                        await self._handle_message_event(task_id, event['messages'], sequence)
                    elif 'output' in event:
                        await self._handle_output_event(task_id, event['output'], sequence)
                    elif 'intermediate_steps' in event:
                        await self._handle_intermediate_event(task_id, event['intermediate_steps'], sequence)
                    else:
                        # Generic event
                        await self._send_event(task_id, event, 'update', sequence)
                        
                elif hasattr(event, 'event') and hasattr(event, 'name'):
                    # Handle LangGraph stream event-like object
                    await self._handle_stream_event(task_id, event, sequence)
                    
                elif isinstance(event, str):
                    # Handle token streaming
                    await self._handle_token(task_id, event, sequence)
                    
                else:
                    # Unknown event type
                    logger.warning(f"Unknown event type: {type(event)}")
                    
            # Flush any remaining tokens
            await self._flush_tokens(task_id, sequence)
            
            # Send completion event
            await self._send_event(
                task_id,
                {"status": "completed"},
                'completed',
                sequence + 1
            )
            
        except Exception as e:
            logger.error(f"Stream conversion error: {e}")
            await self._send_event(
                task_id,
                {"error": str(e), "status": "failed"},
                'failed',
                sequence + 1
            )
            
        finally:
            # Cleanup
            if task_id in self._token_buffer:
                del self._token_buffer[task_id]
                
    async def _handle_message_event(self,
                                  task_id: str,
                                  messages: List[BaseMessage],
                                  sequence: int) -> None:
        """Handle message events from LangGraph.
        
        Args:
            task_id: Task ID
            messages: List of messages
            sequence: Event sequence number
        """
        for message in messages:
            data = {
                "type": message.__class__.__name__,
                "content": message.content,
                "metadata": getattr(message, 'additional_kwargs', {})
            }
            
            event_type = 'human_message' if isinstance(message, HumanMessage) else 'ai_message'
            await self._send_event(task_id, data, event_type, sequence)
            
    async def _handle_output_event(self,
                                 task_id: str,
                                 output: Any,
                                 sequence: int) -> None:
        """Handle output events.
        
        Args:
            task_id: Task ID
            output: Output data
            sequence: Event sequence number
        """
        await self._send_event(
            task_id,
            {"output": output},
            'output',
            sequence
        )
        
    async def _handle_intermediate_event(self,
                                       task_id: str,
                                       steps: List[Any],
                                       sequence: int) -> None:
        """Handle intermediate step events.
        
        Args:
            task_id: Task ID
            steps: Intermediate steps
            sequence: Event sequence number
        """
        for i, step in enumerate(steps):
            await self._send_event(
                task_id,
                {
                    "step": i + 1,
                    "data": step
                },
                'intermediate_step',
                sequence
            )
            
    async def _handle_currency_agent_event(self,
                                         task_id: str,
                                         event: Dict[str, Any],
                                         sequence: int) -> None:
        """Handle CurrencyAgent specific events.
        
        Args:
            task_id: Task ID
            event: CurrencyAgent event
            sequence: Event sequence number
        """
        is_complete = event.get('is_task_complete', False)
        require_input = event.get('require_user_input', False)
        content = event.get('content', '')
        
        # Determine event type
        if is_complete:
            event_type = 'ai_message'
        elif require_input:
            event_type = 'input_required'
        else:
            event_type = 'intermediate_step'
            
        data = {
            "content": content,
            "is_complete": is_complete,
            "require_input": require_input
        }
        
        await self._send_event(task_id, data, event_type, sequence)
            
    async def _handle_stream_event(self,
                                 task_id: str,
                                 event: Any,
                                 sequence: int) -> None:
        """Handle LangGraph stream event.
        
        Args:
            task_id: Task ID
            event: StreamEvent instance
            sequence: Event sequence number
        """
        data = {
            "event": event.event,
            "name": event.name,
            "data": event.data,
            "metadata": event.metadata
        }
        
        await self._send_event(task_id, data, event.event, sequence)
        
    async def _handle_token(self,
                          task_id: str,
                          token: str,
                          sequence: int) -> None:
        """Handle token streaming with batching.
        
        Args:
            task_id: Task ID
            token: Token string
            sequence: Event sequence number
        """
        self._token_buffer[task_id].append(token)
        
        # Send batch if buffer is full
        if len(self._token_buffer[task_id]) >= self.batch_size:
            await self._flush_tokens(task_id, sequence)
            
    async def _flush_tokens(self,
                          task_id: str,
                          sequence: int) -> None:
        """Flush token buffer.
        
        Args:
            task_id: Task ID
            sequence: Event sequence number
        """
        if task_id in self._token_buffer and self._token_buffer[task_id]:
            tokens = ''.join(self._token_buffer[task_id])
            self._token_buffer[task_id] = []
            
            await self._send_event(
                task_id,
                {"tokens": tokens},
                'tokens',
                sequence
            )
            
    async def _send_event(self,
                        task_id: str,
                        data: Any,
                        event_type: str,
                        sequence: int) -> None:
        """Send event to queue.
        
        Args:
            task_id: Task ID
            data: Event data
            event_type: Event type
            sequence: Event sequence number
        """
        event = TaskYieldUpdate(
            task_id=task_id,
            event_type=event_type,
            data=data,
            sequence=sequence
        )
        
        await self.event_queue.put_event(
            task_id,
            event.model_dump()
        )