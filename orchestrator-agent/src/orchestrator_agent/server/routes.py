"""API routes for the orchestrator agent."""

from datetime import datetime
import json

from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

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
    """Handle incoming A2A messages."""
    # Check if client expects streaming based on Accept header
    accept_header = request.headers.get("accept", "")
    
    try:
        if "text/event-stream" in accept_header:
            # Redirect to streaming handler
            return await handle_message_stream(request)
        
        # Parse request
        data = await request.json()
        method, params, request_id = message_handler.parse_jsonrpc_request(data)
        
        if method != "message/send":
            # Check if streaming is expected
            if "text/event-stream" in accept_header:
                async def error_stream():
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": f"Unknown method: {method}",
                            "code": -32601
                        })
                    }
                return EventSourceResponse(error_stream())
            else:
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
        # Check if streaming is expected
        accept_header = request.headers.get("accept", "")
        if "text/event-stream" in accept_header:
            async def error_stream():
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": str(e),
                        "code": -32603
                    })
                }
            return EventSourceResponse(error_stream())
        else:
            return JSONResponse(
                message_handler.create_jsonrpc_error(
                    str(e),
                    -32603,
                    data.get("id") if "data" in locals() else None
                ),
                status_code=500
            )


async def handle_message_stream(request):
    """Handle incoming A2A messages with SSE streaming."""
    import asyncio
    import json
    
    try:
        # Parse request
        data = await request.json()
        method, params, request_id = message_handler.parse_jsonrpc_request(data)
        
        if method != "message/send":
            # Check if streaming is expected
            if "text/event-stream" in accept_header:
                async def error_stream():
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": f"Unknown method: {method}",
                            "code": -32601
                        })
                    }
                return EventSourceResponse(error_stream())
            else:
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
        
        async def event_generator():
            try:
                # Create task
                task = await a2a_executor.create_and_execute_task(a2a_message)
                
                # Send initial response
                yield {
                    "event": "task_created",
                    "data": json.dumps({
                        "taskId": task.taskId,
                        "status": task.status
                    })
                }
                
                # Poll for task completion
                max_polls = 60  # 60 seconds timeout
                for i in range(max_polls):
                    await asyncio.sleep(1)
                    
                    # Get task status
                    updated_task = await task_manager.get_task(task.taskId)
                    if not updated_task:
                        break
                    
                    # Send status update
                    yield {
                        "event": "task_update", 
                        "data": json.dumps({
                            "taskId": updated_task.taskId,
                            "status": updated_task.status
                        })
                    }
                    
                    # If task is complete, send result and finish
                    if updated_task.status in ["completed", "failed", "cancelled"]:
                        yield {
                            "event": "task_complete",
                            "data": json.dumps(updated_task.model_dump(mode="json"))
                        }
                        break
                        
            except Exception as e:
                logger.error("Streaming error", error=str(e))
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }
        
        return EventSourceResponse(event_generator())
        
    except Exception as e:
        logger.error("Error handling stream", error=str(e))
        # Always return SSE format for streaming endpoint
        async def error_stream():
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "code": -32603
                })
            }
        return EventSourceResponse(error_stream())


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


async def cancel_task(request):
    """Cancel a running task."""
    task_id = request.path_params["task_id"]
    
    success = await task_manager.cancel_task(task_id)
    if not success:
        return JSONResponse(
            {"error": "Task not found or already completed"},
            status_code=400
        )
    
    return JSONResponse({"status": "cancelled"})


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


# Define routes
routes = [
    Route("/", handle_message, methods=["POST"]),  # A2A expects message handler at root
    Route("/message", handle_message, methods=["POST"]),
    Route("/message/stream", handle_message_stream, methods=["POST"]),
    Route("/tasks", list_tasks, methods=["GET"]),
    Route("/tasks/{task_id}", get_task, methods=["GET"]),
    Route("/tasks/{task_id}/cancel", cancel_task, methods=["POST"]),
    Route("/.well-known/agent.json", get_agent_card, methods=["GET"]),
    Route("/health", health_check, methods=["GET"]),
]