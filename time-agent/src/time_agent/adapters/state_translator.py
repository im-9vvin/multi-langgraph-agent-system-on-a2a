"""State translation between A2A and LangGraph formats."""

import logging
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class StateTranslator:
    """Translates state between A2A protocol and LangGraph formats."""
    
    @staticmethod
    def a2a_messages_to_langchain(messages: List[Dict[str, Any]]) -> List[Any]:
        """Convert A2A messages to LangChain message format.
        
        Args:
            messages: List of A2A message dictionaries
            
        Returns:
            List of LangChain message objects
        """
        langchain_messages = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                # Default to human message
                logger.warning(f"Unknown role '{role}', defaulting to user")
                langchain_messages.append(HumanMessage(content=content))
        
        return langchain_messages
    
    @staticmethod
    def langchain_messages_to_a2a(messages: List[Any]) -> List[Dict[str, Any]]:
        """Convert LangChain messages to A2A format.
        
        Args:
            messages: List of LangChain message objects
            
        Returns:
            List of A2A message dictionaries
        """
        a2a_messages = []
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                a2a_messages.append({
                    "role": "user",
                    "content": msg.content
                })
            elif isinstance(msg, AIMessage):
                a2a_msg = {
                    "role": "assistant",
                    "content": msg.content
                }
                
                # Include tool calls if present
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    a2a_msg["tool_calls"] = msg.tool_calls
                
                a2a_messages.append(a2a_msg)
            elif isinstance(msg, SystemMessage):
                a2a_messages.append({
                    "role": "system",
                    "content": msg.content
                })
            else:
                # Generic handling
                a2a_messages.append({
                    "role": "unknown",
                    "content": str(msg)
                })
        
        return a2a_messages
    
    @staticmethod
    def create_langgraph_state(
        messages: List[Dict[str, Any]],
        thread_id: str
    ) -> Dict[str, Any]:
        """Create LangGraph compatible state from A2A messages.
        
        Args:
            messages: A2A messages
            thread_id: Thread/conversation ID
            
        Returns:
            LangGraph state dictionary
        """
        return {
            "messages": StateTranslator.a2a_messages_to_langchain(messages),
            "configurable": {
                "thread_id": thread_id
            }
        }
    
    @staticmethod
    def extract_final_response(state: Dict[str, Any]) -> str:
        """Extract final response from LangGraph state.
        
        Args:
            state: LangGraph state
            
        Returns:
            Final response text
        """
        messages = state.get("messages", [])
        
        # Find last AI message
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg.content
        
        return "No response generated"
    
    @staticmethod
    def format_time_response(response_data: Dict[str, Any]) -> str:
        """Format time-specific response data.
        
        Args:
            response_data: Time operation response
            
        Returns:
            Formatted response string
        """
        if "error" in response_data:
            return f"Error: {response_data['error']}"
        
        if "datetime" in response_data:
            # Current time response
            dt_info = response_data["datetime"]
            return (
                f"The current time in {response_data.get('timezone', 'Unknown')} is:\n"
                f"{dt_info.get('formatted', 'Unknown time')}\n"
                f"Timezone: {dt_info.get('timezone_abbreviation', '')}\n"
                f"DST Active: {'Yes' if response_data.get('is_dst', False) else 'No'}"
            )
        
        if "source" in response_data and "target" in response_data:
            # Time conversion response
            source = response_data["source"]
            target = response_data["target"]
            diff = response_data.get("time_difference", {})
            
            return (
                f"Time conversion:\n"
                f"{source.get('time', '')} in {source.get('timezone', '')} is\n"
                f"{target.get('time', '')} in {target.get('timezone', '')}\n"
                f"Time difference: {diff.get('hours', 0)} hours {diff.get('minutes', 0)} minutes"
            )
        
        return str(response_data)