"""Stream conversion utilities for LangGraph to SSE."""

import json
import logging
from typing import Any, AsyncGenerator, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class StreamConverter:
    """Converts LangGraph streaming output to SSE format."""
    
    @staticmethod
    async def convert_agent_stream(
        agent_stream: AsyncGenerator[Any, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Convert LangGraph agent stream to structured events.
        
        Args:
            agent_stream: Raw agent stream
            
        Yields:
            Structured event dictionaries
        """
        try:
            async for chunk in agent_stream:
                # Handle different chunk types from LangGraph
                if isinstance(chunk, dict):
                    # Check for specific LangGraph event types
                    if "messages" in chunk:
                        # Extract and yield message updates
                        for message in chunk["messages"]:
                            yield StreamConverter._convert_message(message)
                    
                    elif "agent" in chunk:
                        # Agent state update
                        yield {
                            "type": "agent_update",
                            "data": chunk["agent"]
                        }
                    
                    elif "tools" in chunk:
                        # Tool invocation
                        yield {
                            "type": "tool_call",
                            "data": chunk["tools"]
                        }
                    
                    else:
                        # Generic update
                        yield {
                            "type": "update",
                            "data": chunk
                        }
                
                else:
                    # Handle other types (strings, etc.)
                    yield {
                        "type": "content",
                        "data": str(chunk)
                    }
        
        except Exception as e:
            logger.error(f"Error converting stream: {e}")
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }
    
    @staticmethod
    def _convert_message(message: Any) -> Dict[str, Any]:
        """Convert a LangChain message to event format.
        
        Args:
            message: LangChain message
            
        Returns:
            Event dictionary
        """
        if isinstance(message, HumanMessage):
            return {
                "type": "human_message",
                "data": {
                    "content": message.content,
                    "role": "user"
                }
            }
        
        elif isinstance(message, AIMessage):
            event_data = {
                "content": message.content,
                "role": "assistant"
            }
            
            # Include tool calls if present
            if hasattr(message, "tool_calls") and message.tool_calls:
                event_data["tool_calls"] = [
                    {
                        "name": tc.get("name"),
                        "args": tc.get("args", {})
                    }
                    for tc in message.tool_calls
                ]
            
            return {
                "type": "ai_message",
                "data": event_data
            }
        
        elif isinstance(message, SystemMessage):
            return {
                "type": "system_message",
                "data": {
                    "content": message.content,
                    "role": "system"
                }
            }
        
        else:
            # Generic message
            return {
                "type": "message",
                "data": {
                    "content": str(message),
                    "role": "unknown"
                }
            }
    
    @staticmethod
    def format_final_response(messages: list) -> Dict[str, Any]:
        """Format the final response from a conversation.
        
        Args:
            messages: List of messages
            
        Returns:
            Final response dictionary
        """
        # Find the last AI message
        last_ai_message = None
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                last_ai_message = message
                break
        
        if last_ai_message:
            return {
                "type": "final_response",
                "data": {
                    "content": last_ai_message.content,
                    "tool_calls": getattr(last_ai_message, "tool_calls", [])
                }
            }
        
        return {
            "type": "final_response",
            "data": {
                "content": "No response generated",
                "tool_calls": []
            }
        }