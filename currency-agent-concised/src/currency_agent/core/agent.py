# Standard library imports
import os
from collections.abc import AsyncIterable
from typing import Any, Dict

# Third-party imports
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# Internal imports
from .state import ResponseFormat
from .tools import get_exchange_rate
from .prompts import SYSTEM_INSTRUCTION, FORMAT_INSTRUCTION


class CurrencyAgent:
    """
    Currency conversion agent using LangGraph.
    
    This agent specializes in currency exchange rate queries using
    the ReAct pattern for tool usage and reasoning.
    
    Key features:
    - Real-time exchange rate lookup via tools
    - Structured response format
    - Multi-turn conversation support
    - Streaming response capability
    """
    
    # List of supported content types for A2A protocol
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    def __init__(self):
        """Initialize the currency agent with LLM and tools."""
        # Create memory saver for conversation persistence
        self.memory = MemorySaver()
        
        # Initialize language model
        model_source = os.getenv('TOOL_MODEL_SRC', 'openai')
        
        if model_source == 'openai':
            self.model = ChatOpenAI(
                model=os.getenv('TOOL_MODEL_NAME', 'gpt-4o-mini'),
                temperature=float(os.getenv('TOOL_MODEL_TEMPERATURE', '0'))
            )
        
        # Agent tools
        self.tools = [get_exchange_rate]
        
        # Create ReAct agent graph
        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=self.memory,
            prompt=SYSTEM_INSTRUCTION,
            response_format=(FORMAT_INSTRUCTION, ResponseFormat),
        )
    
    async def stream(self, query: str, context_id: str) -> AsyncIterable[Dict[str, Any]]:
        """
        Stream agent responses for a user query.
        
        Args:
            query: User's question or request
            context_id: Conversation context identifier
            
        Yields:
            Response items containing status and content
        """
        # Prepare input and config for LangGraph
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}
        
        # Stream agent execution
        async for item in self.graph.astream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            
            # Handle tool calls
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Looking up the exchange rates...',
                }
            # Handle tool responses
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing the exchange rates..',
                }
        
        # Generate final response
        yield await self.get_agent_response(config)
    
    async def get_agent_response(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the final agent response from the current state.
        
        Args:
            config: Current conversation configuration
            
        Returns:
            Response dictionary with status and content
        """
        # Get current graph state
        current_state = await self.graph.aget_state(config)
        structured_response = current_state.values.get('structured_response')
        
        # Process structured response based on status
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == 'input_required':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }
        
        # Fallback response
        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': (
                'We are unable to process your request at the moment. '
                'Please try again.'
            ),
        }