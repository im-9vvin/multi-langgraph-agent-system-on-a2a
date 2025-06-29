"""LangGraph wrapper for integration with A2A protocol."""

import logging
from typing import Any, AsyncGenerator, Dict, Optional

from ..core.agent import TimeAgent
from ..checkpointing.a2a_checkpointer import A2ACheckpointer
from .state_translator import StateTranslator

logger = logging.getLogger(__name__)


class LangGraphWrapper:
    """Wraps LangGraph agent for A2A protocol integration."""
    
    def __init__(
        self,
        agent: TimeAgent,
        checkpointer: Optional[A2ACheckpointer] = None
    ):
        """Initialize wrapper.
        
        Args:
            agent: Time agent instance
            checkpointer: Optional checkpointer for state persistence
        """
        self.agent = agent
        self.checkpointer = checkpointer
        self.state_translator = StateTranslator()
    
    async def execute(
        self,
        messages: list[Dict[str, Any]],
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute agent with A2A messages.
        
        Args:
            messages: A2A format messages
            thread_id: Thread/conversation ID
            checkpoint_id: Optional checkpoint to restore from
            
        Returns:
            Final response data
        """
        try:
            # Create LangGraph state
            state = self.state_translator.create_langgraph_state(
                messages,
                thread_id
            )
            
            # Add checkpointer config if available
            if self.checkpointer and checkpoint_id:
                state["configurable"]["checkpoint_id"] = checkpoint_id
            
            # Execute agent
            result = await self.agent.invoke(state)
            
            # Extract response
            response = self.state_translator.extract_final_response(result)
            
            return {
                "success": True,
                "response": response,
                "messages": self.state_translator.langchain_messages_to_a2a(
                    result.get("messages", [])
                )
            }
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": []
            }
    
    async def stream(
        self,
        messages: list[Dict[str, Any]],
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream agent responses.
        
        Args:
            messages: A2A format messages
            thread_id: Thread/conversation ID
            checkpoint_id: Optional checkpoint to restore from
            
        Yields:
            Streaming events
        """
        try:
            # Create LangGraph state
            state = self.state_translator.create_langgraph_state(
                messages,
                thread_id
            )
            
            # Add checkpointer config if available
            if self.checkpointer and checkpoint_id:
                state["configurable"]["checkpoint_id"] = checkpoint_id
            
            # Stream from agent
            async for chunk in self.agent.stream(state):
                yield {
                    "type": "stream_chunk",
                    "data": chunk
                }
            
            # Send final event
            yield {
                "type": "stream_end",
                "data": {"thread_id": thread_id}
            }
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }
    
    async def get_checkpoints(
        self,
        thread_id: str,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """Get checkpoints for a thread.
        
        Args:
            thread_id: Thread ID
            limit: Maximum number to return
            
        Returns:
            List of checkpoint metadata
        """
        if not self.checkpointer:
            return []
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            checkpoints = await self.checkpointer.alist(config, limit)
            
            return [
                {
                    "checkpoint_id": cp[0]["configurable"].get("checkpoint_id"),
                    "metadata": cp[1].get("metadata", {}),
                    "timestamp": cp[1].get("ts")
                }
                for cp in checkpoints
            ]
            
        except Exception as e:
            logger.error(f"Failed to get checkpoints: {e}")
            return []