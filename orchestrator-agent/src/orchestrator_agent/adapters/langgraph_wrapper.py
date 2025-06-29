"""Wrapper for LangGraph agent with A2A integration."""

from typing import Any, AsyncIterator, Optional

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import Checkpoint

from ..common import get_logger
from ..core import create_orchestrator_agent, OrchestratorState

logger = get_logger(__name__)


class LangGraphWrapper:
    """Wraps LangGraph agent for A2A integration."""
    
    def __init__(self):
        self.agent = create_orchestrator_agent()
    
    async def process_message(
        self,
        message: str,
        context_id: str,
        checkpoint: Optional[Checkpoint] = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Process a message through the orchestrator agent.
        
        Args:
            message: The user message to process
            context_id: The conversation context ID
            checkpoint: Optional checkpoint for resuming state
            
        Yields:
            Agent response chunks
        """
        # Create initial state
        initial_state: OrchestratorState = {
            "messages": [HumanMessage(content=message)],
            "plan": None,
            "routing_decision": None,
            "remote_calls": [],
            "aggregated_results": None,
            "phase": "planning",
            "error": None
        }
        
        # Configure with checkpoint if provided
        config = {"configurable": {"thread_id": context_id}}
        if checkpoint:
            config["checkpoint"] = checkpoint
        
        # Stream the agent execution
        try:
            async for chunk in self.agent.astream(initial_state, config):
                logger.debug("Agent chunk", chunk=chunk)
                
                # Extract relevant information from chunk
                if "messages" in chunk:
                    # Get the latest message
                    messages = chunk["messages"]
                    if messages and hasattr(messages[-1], "content"):
                        yield {
                            "type": "message",
                            "content": messages[-1].content
                        }
                
                if "plan" in chunk and chunk["plan"]:
                    yield {
                        "type": "plan",
                        "content": chunk["plan"]
                    }
                
                if "remote_calls" in chunk and chunk["remote_calls"]:
                    for call in chunk["remote_calls"]:
                        yield {
                            "type": "remote_call",
                            "agent_url": call["agent_url"],
                            "status": call["status"],
                            "result": call.get("result"),
                            "error": call.get("error")
                        }
                
                if "aggregated_results" in chunk and chunk["aggregated_results"]:
                    yield {
                        "type": "final_result",
                        "content": chunk["aggregated_results"].get("response", "")
                    }
                
                if "error" in chunk and chunk["error"]:
                    yield {
                        "type": "error",
                        "content": chunk["error"]
                    }
        
        except Exception as e:
            logger.error("Error in agent execution", error=str(e))
            yield {
                "type": "error",
                "content": f"Agent execution error: {str(e)}"
            }
    
    def get_checkpoint(self, thread_id: str) -> Optional[Checkpoint]:
        """Get checkpoint for a thread."""
        try:
            return self.agent.checkpointer.get({"configurable": {"thread_id": thread_id}})
        except Exception as e:
            logger.error("Failed to get checkpoint", thread_id=thread_id, error=str(e))
            return None