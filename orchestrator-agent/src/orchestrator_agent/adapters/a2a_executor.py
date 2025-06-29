"""A2A executor that orchestrates the full flow."""

from typing import Optional


from ..common import get_logger
from ..protocol.models import A2AMessage, TaskStatus
from ..protocol.task_manager import TaskManager
from .langgraph_wrapper import LangGraphWrapper

logger = get_logger(__name__)


class A2AExecutor:
    """Executes A2A tasks using the orchestrator agent."""
    
    def __init__(self):
        self.task_manager = TaskManager()
        self.agent_wrapper = LangGraphWrapper()
    
    async def execute_task(
        self,
        message: A2AMessage,
        task_id: str
    ) -> None:
        """Execute an A2A task.
        
        Args:
            message: The A2A message to process
            task_id: The task ID to update
        """
        
        try:
            # Update task status to in_progress
            await self.task_manager.update_task_status(task_id, "in_progress")
            
            # Extract text from message parts
            text_parts = []
            for part in message.parts:
                if "text" in part:
                    text_parts.append(part["text"])
            
            if not text_parts:
                raise ValueError("No text content in message")
            
            full_message = " ".join(text_parts)
            context_id = message.contextId or "default"
            
            # Process through agent
            final_response = ""
            intermediate_results = []
            
            async for chunk in self.agent_wrapper.process_message(
                full_message, 
                context_id
            ):
                chunk_type = chunk.get("type")
                
                if chunk_type == "message":
                    # Intermediate message from agent
                    content = chunk.get("content", "")
                    if content:
                        intermediate_results.append(content)
                
                elif chunk_type == "plan":
                    # Store plan in task result
                    await self.task_manager.update_task_status(
                        task_id,
                        "in_progress",
                        result={"plan": chunk.get("content", "")}
                    )
                
                elif chunk_type == "remote_call":
                    # Log remote call status
                    agent_url = chunk.get("agent_url")
                    status = chunk.get("status")
                    logger.info(f"Remote call to {agent_url}: {status}")
                
                elif chunk_type == "final_result":
                    # Final aggregated result
                    final_response = chunk.get("content", "")
                
                elif chunk_type == "error":
                    # Handle error
                    error_msg = chunk.get("content", "Unknown error")
                    logger.error("Agent error", error=error_msg)
                    await self.task_manager.update_task_status(
                        task_id,
                        "failed",
                        error=error_msg
                    )
                    return
            
            # Prepare final result
            if final_response:
                result_text = final_response
            elif intermediate_results:
                result_text = "\n\n".join(intermediate_results)
            else:
                result_text = "No response generated"
            
            # Complete the task with result
            await self.task_manager.update_task_status(
                task_id,
                "completed",
                result={
                    "artifacts": [{
                        "data": result_text,
                        "name": "response.txt",
                        "mimeType": "text/plain"
                    }]
                }
            )
            
        except Exception as e:
            logger.error("Task execution failed", task_id=task_id, error=str(e))
            await self.task_manager.update_task_status(
                task_id,
                "failed",
                error=str(e)
            )
    
    async def create_and_execute_task(
        self,
        message: A2AMessage
    ) -> TaskStatus:
        """Create task record and execute it.
        
        Args:
            message: The A2A message to process
            
        Returns:
            The created task status
        """
        # Create task record
        task = await self.task_manager.create_task(message)
        
        # Execute task asynchronously
        # Note: In production, this would be queued
        import asyncio
        asyncio.create_task(self.execute_task(message, task.taskId))
        
        return task