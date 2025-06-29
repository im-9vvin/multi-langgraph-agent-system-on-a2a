"""API routes for the time agent server."""

import logging
from typing import Optional

from a2a.server.request_handlers import DefaultRequestHandler
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from ..adapters.a2a_executor import TimeAgentExecutor
from ..common.config import settings
from ..protocol.agent_card_generator import AgentCardGenerator
from ..protocol.models import TaskStatus
from ..streaming.sse_handler import SSEHandler
from .models import ErrorResponse, HealthResponse, TaskListResponse

logger = logging.getLogger(__name__)


class TimeAgentRoutes:
    """Manages routes for the time agent server."""
    
    def __init__(self, request_handler: DefaultRequestHandler, executor: TimeAgentExecutor):
        """Initialize routes.
        
        Args:
            request_handler: A2A request handler
            executor: Agent executor
        """
        self.request_handler = request_handler
        self.executor = executor
        self.sse_handler = SSEHandler(executor.stream_event_queue)
        self.agent_card_generator = AgentCardGenerator()
    
    async def health(self, request: Request) -> JSONResponse:
        """Health check endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Health status response
        """
        try:
            # Get metrics from middleware if available
            metrics = None
            if hasattr(request.app.state, "metrics_middleware"):
                metrics = request.app.state.metrics_middleware.get_metrics()
            
            health_info = self.agent_card_generator.generate_health_info()
            
            # Add runtime metrics
            if metrics:
                health_info["metrics"] = metrics
            
            response = HealthResponse(
                status="healthy",
                version="1.0.0",
                timestamp=datetime.utcnow(),
                services=health_info.get("services", {}),
                metrics=health_info.get("metrics")
            )
            
            return JSONResponse(content=response.model_dump())
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return JSONResponse(
                content={"status": "unhealthy", "error": str(e)},
                status_code=503
            )
    
    async def agent_info(self, request: Request) -> JSONResponse:
        """Agent discovery endpoint (.well-known/agent.json).
        
        Args:
            request: HTTP request
            
        Returns:
            Agent metadata response
        """
        agent_card = self.agent_card_generator.generate()
        return JSONResponse(content=agent_card)
    
    async def list_tasks(self, request: Request) -> JSONResponse:
        """List tasks endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Task list response
        """
        try:
            # Get query parameters
            status = request.query_params.get("status")
            limit = int(request.query_params.get("limit", "10"))
            page = int(request.query_params.get("page", "1"))
            
            # Convert status string to enum if provided
            task_status = None
            if status:
                try:
                    task_status = TaskStatus(status)
                except ValueError:
                    return JSONResponse(
                        content={"error": f"Invalid status: {status}"},
                        status_code=400
                    )
            
            # Get tasks from task manager
            all_tasks = await self.executor.task_manager.list_tasks(
                status=task_status,
                limit=limit * page  # Get enough for pagination
            )
            
            # Paginate
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            tasks = all_tasks[start_idx:end_idx]
            
            # Convert to response format
            task_dicts = [task.model_dump() for task in tasks]
            
            response = TaskListResponse(
                tasks=task_dicts,
                total=len(all_tasks),
                page=page,
                limit=limit
            )
            
            return JSONResponse(content=response.model_dump())
            
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return JSONResponse(
                content={"error": str(e)},
                status_code=500
            )
    
    async def get_task(self, request: Request) -> JSONResponse:
        """Get specific task details.
        
        Args:
            request: HTTP request
            
        Returns:
            Task details response
        """
        task_id = request.path_params.get("task_id")
        
        if not task_id:
            return JSONResponse(
                content={"error": "Task ID required"},
                status_code=400
            )
        
        try:
            task = await self.executor.task_manager.get_task(task_id)
            
            if not task:
                return JSONResponse(
                    content={"error": f"Task {task_id} not found"},
                    status_code=404
                )
            
            return JSONResponse(content=task.model_dump())
            
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return JSONResponse(
                content={"error": str(e)},
                status_code=500
            )
    
    async def stream_messages(self, request: Request) -> StreamingResponse:
        """SSE endpoint for streaming messages.
        
        Args:
            request: HTTP request
            
        Returns:
            Streaming response
        """
        # Get client ID and last event ID from headers
        client_id = request.headers.get("X-Client-ID")
        last_event_id = request.headers.get("Last-Event-ID")
        
        logger.info(f"Starting SSE stream for client {client_id}")
        
        return self.sse_handler.create_response(
            client_id=client_id,
            last_event_id=last_event_id
        )
    
    async def stream_task(self, request: Request) -> StreamingResponse:
        """SSE endpoint for streaming task updates.
        
        Args:
            request: HTTP request
            
        Returns:
            Streaming response for specific task
        """
        task_id = request.path_params.get("task_id")
        
        if not task_id:
            return JSONResponse(
                content={"error": "Task ID required"},
                status_code=400
            )
        
        # Create task-specific SSE stream
        async def task_event_stream():
            """Stream events for specific task."""
            queue = await self.executor.task_manager.get_task_updates(task_id)
            
            while True:
                try:
                    update = await queue.get()
                    yield self.sse_handler.formatter.format_task_event(
                        task_id=task_id,
                        event_type=update.event_type,
                        data=update.data
                    )
                except Exception as e:
                    logger.error(f"Error streaming task {task_id}: {e}")
                    yield self.sse_handler.formatter.format_event(
                        data={"error": str(e)},
                        event="error"
                    )
                    break
        
        return StreamingResponse(
            task_event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )


# Missing import
from datetime import datetime