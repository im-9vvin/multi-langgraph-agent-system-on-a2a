"""Core agent implementation using LangGraph."""

import logging
import os
from typing import Any, Dict, Optional

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent

from .prompts import SYSTEM_PROMPT
from .state import TimeAgentState
from .tools import TimeTools

logger = logging.getLogger(__name__)


class TimeAgent:
    """Time agent using LangGraph for conversational time assistance."""
    
    def __init__(
        self,
        model: Optional[ChatOpenAI] = None,
        local_timezone: Optional[str] = None
    ):
        """Initialize the time agent.
        
        Args:
            model: Optional ChatOpenAI model instance
            local_timezone: Optional local timezone override
        """
        self.model = model or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            streaming=True,
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        
        # Initialize tools
        self.time_tools = TimeTools(local_timezone=local_timezone)
        self.tools = self.time_tools.get_langchain_tools()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        # Create a ReAct agent with our tools
        # Update the model with system prompt
        model_with_system = self.model.bind(
            system=SYSTEM_PROMPT
        )
        
        agent = create_react_agent(
            model_with_system,
            self.tools
        )
        
        return agent
    
    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the agent with the given state.
        
        Args:
            state: Input state dictionary
            
        Returns:
            Updated state dictionary
        """
        try:
            result = await self.graph.ainvoke(state)
            return result
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}")
            raise
    
    async def stream(self, state: Dict[str, Any]):
        """Stream agent responses.
        
        Args:
            state: Input state dictionary
            
        Yields:
            State updates and messages
        """
        try:
            async for chunk in self.graph.astream(state):
                yield chunk
        except Exception as e:
            logger.error(f"Agent streaming failed: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources."""
        await self.time_tools.cleanup()