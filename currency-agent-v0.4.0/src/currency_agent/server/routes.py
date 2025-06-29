"""HTTP endpoint routing for v0.4.0 architecture."""

import logging
from typing import Optional

from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.routing import Route

from ..streaming import SSEHandler
from ..protocol import TaskManager, AgentCardGenerator
from ..protocol.models import TaskStatus


logger = logging.getLogger(__name__)


class RouterV040:
    """HTTP router for v0.4.0 endpoints."""
    
    def __init__(self,
                 task_manager: TaskManager,
                 sse_handler: SSEHandler,
                 agent_card_generator: AgentCardGenerator):
        """Initialize router with dependencies.
        
        Args:
            task_manager: Task management instance
            sse_handler: SSE handler for streaming
            agent_card_generator: Agent card generator
        """
        self.task_manager = task_manager
        self.sse_handler = sse_handler
        self.agent_card_generator = agent_card_generator
        
    def get_routes(self) -> list[Route]:
        """Get Starlette routes.
        
        Returns:
            List of configured routes
        """
        return [
            # Streaming endpoints
            Route("/message/stream", self.message_stream, methods=["POST"]),
            Route("/tasks/{task_id}/stream", self.task_stream, methods=["GET"]),
            Route("/tasks/sendSubscribe", self.task_subscribe, methods=["POST"]),
            
            # Task management endpoints
            Route("/tasks", self.list_tasks, methods=["GET"]),
            Route("/tasks/{task_id}", self.get_task, methods=["GET"]),
            Route("/tasks/{task_id}/cancel", self.cancel_task, methods=["POST"]),
            
            # Agent discovery
            Route("/.well-known/agent.json", self.agent_card, methods=["GET"]),
            
            # Health check
            Route("/health", self.health_check, methods=["GET"]),
        ]
        
    async def message_stream(self, request: Request) -> Response:
        """Handle streaming message endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            SSE streaming response
        """
        try:
            # Parse request body
            data = await request.json()
            task_id = data.get("taskId") or data.get("task_id")
            
            if not task_id:
                return JSONResponse(
                    {"error": "task_id required"},
                    status_code=400
                )
                
            # Create SSE response
            return await self.sse_handler.create_sse_response(request, task_id)
            
        except Exception as e:
            logger.error(f"Message stream error: {e}")
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )
            
    async def task_stream(self, request: Request) -> Response:
        """Stream events for a specific task.
        
        Args:
            request: HTTP request
            
        Returns:
            SSE streaming response
        """
        task_id = request.path_params["task_id"]
        
        try:
            # Verify task exists
            await self.task_manager.get_task(task_id)
            
            # Create SSE response
            return await self.sse_handler.create_sse_response(request, task_id)
            
        except Exception as e:
            logger.error(f"Task stream error: {e}")
            return JSONResponse(
                {"error": str(e)},
                status_code=404 if "not found" in str(e).lower() else 500
            )
            
    async def task_subscribe(self, request: Request) -> Response:
        """Subscribe to task events.
        
        Args:
            request: HTTP request
            
        Returns:
            SSE streaming response
        """
        try:
            # Parse subscription request
            data = await request.json()
            task_ids = data.get("taskIds", [])
            
            if not task_ids:
                return JSONResponse(
                    {"error": "taskIds required"},
                    status_code=400
                )
                
            # For now, subscribe to first task
            # TODO: Implement multi-task subscription
            task_id = task_ids[0]
            
            return await self.sse_handler.create_sse_response(request, task_id)
            
        except Exception as e:
            logger.error(f"Task subscribe error: {e}")
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )
            
    async def list_tasks(self, request: Request) -> JSONResponse:
        """List tasks with optional filtering.
        
        Args:
            request: HTTP request
            
        Returns:
            JSON response with task list
        """
        try:
            # Parse query parameters
            status = request.query_params.get("status")
            limit = int(request.query_params.get("limit", "100"))
            
            # Convert status string to enum if provided
            task_status = None
            if status:
                try:
                    task_status = TaskStatus(status)
                except ValueError:
                    return JSONResponse(
                        {"error": f"Invalid status: {status}"},
                        status_code=400
                    )
                    
            # List tasks
            tasks = await self.task_manager.list_tasks(
                status=task_status,
                limit=limit
            )
            
            # Convert to JSON-serializable format
            return JSONResponse({
                "tasks": [task.model_dump() for task in tasks],
                "total": len(tasks)
            })
            
        except Exception as e:
            logger.error(f"List tasks error: {e}")
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )
            
    async def get_task(self, request: Request) -> JSONResponse:
        """Get specific task details.
        
        Args:
            request: HTTP request
            
        Returns:
            JSON response with task details
        """
        task_id = request.path_params["task_id"]
        
        try:
            task = await self.task_manager.get_task(task_id)
            return JSONResponse(task.model_dump())
            
        except Exception as e:
            logger.error(f"Get task error: {e}")
            return JSONResponse(
                {"error": str(e)},
                status_code=404 if "not found" in str(e).lower() else 500
            )
            
    async def cancel_task(self, request: Request) -> JSONResponse:
        """Cancel a running task.
        
        Args:
            request: HTTP request
            
        Returns:
            JSON response with cancellation result
        """
        task_id = request.path_params["task_id"]
        
        try:
            # Update task status
            task = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.CANCELLED
            )
            
            # Close SSE connection if active
            self.sse_handler.close_connection(task_id)
            
            return JSONResponse({
                "status": "cancelled",
                "task": task.model_dump()
            })
            
        except Exception as e:
            logger.error(f"Cancel task error: {e}")
            return JSONResponse(
                {"error": str(e)},
                status_code=404 if "not found" in str(e).lower() else 500
            )
            
    async def agent_card(self, request: Request) -> JSONResponse:
        """Return agent discovery card.
        
        Args:
            request: HTTP request
            
        Returns:
            JSON response with agent card
        """
        # Generate agent card
        card = self.agent_card_generator.generate_card(
            description="Currency Exchange Agent with A2A Protocol v0.4.0",
            capabilities=[
                "currency_conversion",
                "exchange_rate_lookup",
                "streaming_responses",
                "task_checkpointing"
            ]
        )
        
        return JSONResponse(card.model_dump())
        
    async def health_check(self, request: Request) -> JSONResponse:
        """Health check endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            JSON response with health status
        """
        return JSONResponse({
            "status": "healthy",
            "version": "0.4.0",
            "active_tasks": len(self.task_manager.tasks)
        })