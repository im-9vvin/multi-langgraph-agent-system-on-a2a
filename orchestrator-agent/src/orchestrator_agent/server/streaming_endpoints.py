"""Streaming endpoints for the orchestrator agent."""

import logging
from starlette.responses import StreamingResponse
from starlette.requests import Request

from ..adapters import OrchestratorExecutor
from ..common.logging import get_logger

logger = get_logger(__name__)


def add_streaming_endpoints(app, executor: OrchestratorExecutor):
    """Add streaming endpoints to the application.
    
    Args:
        app: A2A Starlette application
        executor: Orchestrator executor instance
    """
    # Get the underlying Starlette app
    starlette_app = app.build()
    
    @starlette_app.route("/stream/{context_id}", methods=["GET"])
    async def stream_events(request: Request):
        """SSE endpoint for streaming orchestration events.
        
        Args:
            request: HTTP request
            
        Returns:
            StreamingResponse with SSE events
        """
        context_id = request.path_params["context_id"]
        
        async def event_generator():
            """Generate SSE events."""
            try:
                # Set SSE headers
                yield "retry: 10000\n\n"
                
                # Subscribe to events for this context
                async for event in executor.streaming_handler.subscribe(context_id):
                    yield event.to_sse()
                    
            except Exception as e:
                logger.error(f"Error streaming events: {e}")
                yield f"event: error\ndata: {{'error': '{str(e)}'}}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    @starlette_app.route("/protocol/status/{task_id}", methods=["GET"])
    async def get_task_status(request: Request):
        """Get task status from protocol handler.
        
        Args:
            request: HTTP request
            
        Returns:
            JSON response with task status
        """
        task_id = request.path_params["task_id"]
        task = executor.protocol_handler.get_task(task_id)
        
        if not task:
            return {"error": f"Task {task_id} not found"}, 404
            
        return task.to_dict()
    
    @starlette_app.route("/protocol/tasks/{context_id}", methods=["GET"])
    async def get_context_tasks(request: Request):
        """Get all tasks for a context.
        
        Args:
            request: HTTP request
            
        Returns:
            JSON response with tasks
        """
        context_id = request.path_params["context_id"]
        tasks = executor.protocol_handler.get_tasks_by_context(context_id)
        
        return {
            "context_id": context_id,
            "tasks": [task.to_dict() for task in tasks]
        }
    
    @starlette_app.route("/checkpoints/{thread_id}/export", methods=["GET"])
    async def export_checkpoint(request: Request):
        """Export checkpoint history for a thread.
        
        Args:
            request: HTTP request
            
        Returns:
            JSON response with export path
        """
        thread_id = request.path_params["thread_id"]
        
        try:
            export_path = executor.checkpoint_manager.export_thread_history(thread_id)
            return {
                "status": "success",
                "export_path": export_path
            }
        except Exception as e:
            logger.error(f"Error exporting checkpoint: {e}")
            return {"error": str(e)}, 500
    
    logger.info("Added streaming endpoints to application")