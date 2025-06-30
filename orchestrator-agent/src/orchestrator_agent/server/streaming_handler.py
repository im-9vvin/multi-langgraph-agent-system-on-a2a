"""Streaming request handler for A2A protocol."""

import asyncio
import json
import logging
from typing import AsyncIterator, Optional
from starlette.responses import StreamingResponse
from starlette.requests import Request

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater, InMemoryTaskStore, InMemoryPushNotifier
from a2a.types import (
    Task,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    SendStreamingMessageResponse,
    InvalidParamsError,
)
from a2a.utils import new_task
from a2a.utils.errors import ServerError

logger = logging.getLogger(__name__)


class StreamingRequestHandler(DefaultRequestHandler):
    """Request handler that supports A2A streaming via SSE."""
    
    def __init__(
        self,
        agent_executor: AgentExecutor,
        task_store=None,
        push_notifier=None,
    ):
        """Initialize streaming request handler.
        
        Args:
            agent_executor: Agent executor instance
            task_store: Task store (optional)
            push_notifier: Push notifier (optional)
        """
        super().__init__(
            agent_executor=agent_executor,
            task_store=task_store or InMemoryTaskStore(),
            push_notifier=push_notifier or InMemoryPushNotifier(None),
        )
    
    async def handle_request(self, request: Request):
        """Handle incoming HTTP request.
        
        Args:
            request: Starlette Request object
            
        Returns:
            Response object (JSON or SSE stream)
        """
        # Parse JSON-RPC request
        try:
            data = await request.json()
        except Exception:
            return {"error": {"code": -32700, "message": "Parse error"}}
        
        method = data.get("method")
        
        # Check if this is a streaming request
        if method == "message/stream":
            # Return SSE streaming response
            return StreamingResponse(
                self._stream_response(data),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # For non-streaming requests, use parent handler
        return await super().handle_request(request)
    
    async def _stream_response(self, request_data: dict) -> AsyncIterator[str]:
        """Generate SSE stream for message/stream request.
        
        Args:
            request_data: JSON-RPC request data
            
        Yields:
            SSE formatted strings
        """
        request_id = request_data.get("id", 1)
        params = request_data.get("params", {})
        
        try:
            # Create request context
            message = params.get("message", {})
            context = RequestContext(message=message)
            
            # Create event queue for streaming
            event_queue = EventQueue()
            
            # Get or create task
            sdk_task = context.current_task
            if not sdk_task:
                sdk_task = new_task(context.message)
                # Send initial task as first SSE event
                yield self._format_sse_event({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": sdk_task.to_dict()
                })
            
            # Create updater
            updater = TaskUpdater(event_queue, sdk_task.id, sdk_task.contextId)
            
            # Start agent execution in background
            execution_task = asyncio.create_task(
                self._execute_with_streaming(context, event_queue)
            )
            
            # Stream events as they come
            try:
                while True:
                    # Get next event with timeout
                    try:
                        event = await asyncio.wait_for(
                            event_queue.dequeue_event(),
                            timeout=0.1
                        )
                        
                        if event:
                            # Format as SSE data
                            response = SendStreamingMessageResponse(
                                jsonrpc="2.0",
                                id=request_id,
                                result=event
                            )
                            yield self._format_sse_event(response.to_dict())
                            
                            # Check if this is the final event
                            if hasattr(event, 'final') and event.final:
                                break
                                
                    except asyncio.TimeoutError:
                        # Check if execution is done
                        if execution_task.done():
                            # Get any remaining events
                            while True:
                                event = await event_queue.dequeue_event()
                                if not event:
                                    break
                                response = SendStreamingMessageResponse(
                                    jsonrpc="2.0",
                                    id=request_id,
                                    result=event
                                )
                                yield self._format_sse_event(response.to_dict())
                            break
                            
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                # Send error event
                error_event = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                yield self._format_sse_event(error_event)
                
        except Exception as e:
            logger.error(f"Stream setup error: {e}")
            error_event = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            yield self._format_sse_event(error_event)
    
    async def _execute_with_streaming(self, context: RequestContext, event_queue: EventQueue):
        """Execute agent with streaming support.
        
        Args:
            context: Request context
            event_queue: Event queue for streaming
        """
        try:
            # Check if executor has execute_stream method
            if hasattr(self.agent_executor, 'execute_stream'):
                await self.agent_executor.execute_stream(context, event_queue)
            else:
                # Fallback to regular execute
                await self.agent_executor.execute(context, event_queue)
        except Exception as e:
            logger.error(f"Execution error: {e}")
            raise
    
    def _format_sse_event(self, data: dict) -> str:
        """Format data as SSE event.
        
        Args:
            data: Data to send
            
        Returns:
            SSE formatted string
        """
        json_data = json.dumps(data, ensure_ascii=False)
        return f"data: {json_data}\n\n"