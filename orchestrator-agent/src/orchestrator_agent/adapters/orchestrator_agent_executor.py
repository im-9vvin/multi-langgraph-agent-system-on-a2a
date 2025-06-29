"""A2A Protocol executor for Orchestrator Agent."""

import logging
from typing import Optional

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TextPart,
)
from a2a.utils import new_agent_text_message

from ..core.agent import create_orchestrator_agent
from ..common import get_logger

logger = get_logger(__name__)


class OrchestratorAgentExecutor(AgentExecutor):
    """A2A Protocol executor for Orchestrator Agent."""
    
    def __init__(self):
        """Initialize executor."""
        self.agent = create_orchestrator_agent()
    
    async def execute(
        self,
        request_context: RequestContext,
        task_updater: TaskUpdater
    ) -> None:
        """Execute an orchestration request.
        
        Args:
            request_context: A2A request context
            task_updater: Task updater for status updates
        """
        try:
            # Extract text from message parts
            text_parts = []
            for part in request_context.message.parts:
                if isinstance(part, TextPart):
                    text_parts.append(part.text)
            
            if not text_parts:
                raise InvalidParamsError("No text content in message")
            
            full_message = " ".join(text_parts)
            
            # Update task status
            await task_updater.update_status("Processing orchestration request")
            
            # Process through orchestrator agent
            result = await self.agent.ainvoke({
                "messages": [{"role": "user", "content": full_message}],
                "plan": None,
                "routing_decision": None,
                "remote_calls": [],
                "aggregated_results": None,
                "phase": "planning",
                "error": None
            })
            
            # Extract final response
            if result.get("error"):
                raise InternalError(f"Orchestration failed: {result['error']}")
            
            response_text = "No response generated"
            if result.get("aggregated_results"):
                response_text = result["aggregated_results"].get("response", response_text)
            elif result.get("messages"):
                # Get last assistant message
                for msg in reversed(result["messages"]):
                    if msg.get("role") == "assistant":
                        response_text = msg.get("content", response_text)
                        break
            
            # Send response
            await task_updater.add_message(
                new_agent_text_message(response_text)
            )
            
            # Mark complete
            await task_updater.complete()
            
        except Exception as e:
            logger.error("Orchestration failed", error=str(e))
            await task_updater.fail(str(e))