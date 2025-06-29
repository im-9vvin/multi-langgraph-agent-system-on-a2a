"""Wrapper for LangGraph agents to work with A2A protocol."""

import logging
from typing import Any, AsyncIterator, Dict, Optional

from langchain_core.runnables import RunnableConfig

from ..core.agent import CurrencyAgent
from ..checkpointing import A2ACheckpointer


logger = logging.getLogger(__name__)


class LangGraphWrapper:
    """
    Wraps LangGraph agents for A2A protocol compatibility.
    
    Provides:
    - Checkpointing integration
    - Stream handling
    - Configuration management
    - Error handling
    """
    
    def __init__(self, agent: CurrencyAgent, checkpointer: Optional[A2ACheckpointer] = None):
        """Initialize wrapper with agent and optional checkpointer.
        
        Args:
            agent: LangGraph agent instance
            checkpointer: Optional A2A checkpointer
        """
        self.agent = agent
        self.checkpointer = checkpointer
        
    async def astream(self,
                     query: str,
                     thread_id: str,
                     config: Optional[Dict[str, Any]] = None) -> AsyncIterator[Any]:
        """Stream agent execution with checkpointing.
        
        Args:
            query: User query
            thread_id: Thread ID for checkpointing
            config: Optional additional configuration
            
        Yields:
            Stream events from agent
        """
        # Prepare configuration
        runnable_config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Add checkpointer if available
        if self.checkpointer:
            runnable_config["checkpointer"] = self.checkpointer
            
        # Merge with provided config
        if config:
            runnable_config.update(config)
            
        try:
            # Stream from agent
            async for event in self.agent.stream(query, thread_id):
                yield event
                
        except Exception as e:
            logger.error(f"Agent streaming error: {e}")
            # Yield error event
            yield {
                "error": str(e),
                "type": "error"
            }
            raise
            
    async def ainvoke(self,
                     query: str,
                     thread_id: str,
                     config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke agent without streaming.
        
        Args:
            query: User query
            thread_id: Thread ID for checkpointing
            config: Optional additional configuration
            
        Returns:
            Agent response
        """
        # Collect all events from stream
        events = []
        async for event in self.astream(query, thread_id, config):
            events.append(event)
            
        # Return last event as result
        if events:
            return events[-1]
        else:
            return {"error": "No response from agent"}
            
    async def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get current state from checkpointer.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Current state or None
        """
        if not self.checkpointer:
            return None
            
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        checkpoint_tuple = await self.checkpointer.aget_tuple(config)
        if checkpoint_tuple:
            return checkpoint_tuple.checkpoint
        return None
        
    async def update_state(self,
                          thread_id: str,
                          state_updates: Dict[str, Any]) -> None:
        """Update state in checkpointer.
        
        Args:
            thread_id: Thread ID
            state_updates: State updates to apply
        """
        if not self.checkpointer:
            logger.warning("No checkpointer available for state update")
            return
            
        # Get current state
        current_state = await self.get_state(thread_id) or {"v": 1, "data": {}}
        
        # Merge updates
        current_state["data"].update(state_updates)
        
        # Save updated state
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        await self.checkpointer.aput(
            config=config,
            checkpoint=current_state,
            metadata={
                "source": "manual_update",
                "updates": list(state_updates.keys())
            }
        )