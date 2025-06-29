"""Simple API routes for the orchestrator agent."""

from datetime import datetime

from starlette.responses import JSONResponse
from starlette.routing import Route

from ..adapters import A2AExecutor
from ..common import get_logger
from ..protocol import MessageHandler
from .models import create_agent_card
from ..protocol.task_manager import TaskManager

logger = get_logger(__name__)

# Global instances
a2a_executor = A2AExecutor()
task_manager = a2a_executor.task_manager
message_handler = MessageHandler()


async def handle_message(request):
    """Handle incoming A2A messages - simple JSON response."""
    try:
        # Parse request
        data = await request.json()
        method, params, request_id = message_handler.parse_jsonrpc_request(data)
        
        if method != "message/send":
            return JSONResponse(
                message_handler.create_jsonrpc_error(
                    f"Unknown method: {method}",
                    -32601,
                    request_id
                ),
                status_code=400
            )
        
        # Extract and validate message
        a2a_message = message_handler.extract_a2a_message(params)
        
        # Create and execute task
        task = await a2a_executor.create_and_execute_task(a2a_message)
        
        # Return task response
        response = message_handler.create_jsonrpc_response(
            message_handler.format_task_response(task.taskId, task.status),
            request_id
        )
        
        return JSONResponse(response)
        
    except Exception as e:
        logger.error("Error handling message", error=str(e))
        return JSONResponse(
            message_handler.create_jsonrpc_error(
                str(e),
                -32603,
                data.get("id") if "data" in locals() else None
            ),
            status_code=500
        )


async def get_task(request):
    """Get task status."""
    task_id = request.path_params["task_id"]
    
    task = await task_manager.get_task(task_id)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    return JSONResponse(task.model_dump(mode="json"))


async def list_tasks(request):
    """List tasks with optional filtering."""
    status = request.query_params.get("status")
    limit = int(request.query_params.get("limit", 100))
    
    tasks = await task_manager.list_tasks(status=status, limit=limit)
    
    return JSONResponse({
        "tasks": [t.model_dump(mode="json") for t in tasks],
        "count": len(tasks)
    })


async def get_agent_card(request):
    """Get agent card for discovery."""
    from ..common.config import config
    card = create_agent_card(config.a2a_host, config.a2a_port)
    return JSONResponse(card)


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.4.0",
        "agent": "orchestrator-agent"
    })


# Define routes - A2A compliant without SSE complexity
routes = [
    Route("/", handle_message, methods=["POST"]),
    Route("/message", handle_message, methods=["POST"]),
    Route("/tasks", list_tasks, methods=["GET"]),
    Route("/tasks/{task_id}", get_task, methods=["GET"]),
    Route("/.well-known/agent.json", get_agent_card, methods=["GET"]),
    Route("/health", health_check, methods=["GET"]),
]