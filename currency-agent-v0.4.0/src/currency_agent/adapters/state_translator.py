"""State translator between different formats in the system."""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from a2a.types import Part, TextPart

from ..protocol.models import TaskYieldUpdate


logger = logging.getLogger(__name__)


class StateTranslator:
    """
    Translates between different state representations:
    - LangGraph state <-> A2A protocol state
    - SSE events <-> A2A events
    - LangChain messages <-> A2A parts
    """
    
    def langgraph_to_a2a_state(self, langgraph_state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert LangGraph state to A2A protocol state.
        
        Args:
            langgraph_state: State from LangGraph
            
        Returns:
            A2A compatible state
        """
        a2a_state = {
            "messages": [],
            "context": {},
            "metadata": {}
        }
        
        # Convert messages
        if "messages" in langgraph_state:
            a2a_state["messages"] = [
                self._convert_message_to_a2a(msg)
                for msg in langgraph_state["messages"]
            ]
            
        # Convert other state data
        for key, value in langgraph_state.items():
            if key != "messages":
                # Store in context
                a2a_state["context"][key] = value
                
        return a2a_state
        
    def a2a_to_langgraph_state(self, a2a_state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert A2A protocol state to LangGraph state.
        
        Args:
            a2a_state: State from A2A protocol
            
        Returns:
            LangGraph compatible state
        """
        langgraph_state = {}
        
        # Convert messages
        if "messages" in a2a_state:
            langgraph_state["messages"] = [
                self._convert_a2a_to_message(msg)
                for msg in a2a_state["messages"]
            ]
            
        # Add context data
        if "context" in a2a_state:
            langgraph_state.update(a2a_state["context"])
            
        return langgraph_state
        
    def _convert_message_to_a2a(self, message: BaseMessage) -> Dict[str, Any]:
        """Convert LangChain message to A2A format.
        
        Args:
            message: LangChain message
            
        Returns:
            A2A message format
        """
        parts: List[Part] = []
        
        # Convert content to parts
        if isinstance(message.content, str):
            parts.append(TextPart(text=message.content))
        elif isinstance(message.content, list):
            # Handle multi-modal content
            for content in message.content:
                if isinstance(content, str):
                    parts.append(TextPart(text=content))
                elif isinstance(content, dict):
                    if content.get("type") == "text":
                        parts.append(TextPart(text=content.get("text", "")))
                    # Add more content type handling as needed
                    
        # Determine role
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        elif isinstance(message, SystemMessage):
            role = "system"
        else:
            role = "unknown"
            
        return {
            "role": role,
            "parts": [part.model_dump() for part in parts],
            "metadata": message.additional_kwargs
        }
        
    def _convert_a2a_to_message(self, a2a_msg: Dict[str, Any]) -> BaseMessage:
        """Convert A2A message to LangChain format.
        
        Args:
            a2a_msg: A2A message
            
        Returns:
            LangChain message
        """
        # Extract text from parts
        text_parts = []
        for part in a2a_msg.get("parts", []):
            if part.get("type") == "text":
                text_parts.append(part.get("text", ""))
                
        content = "\n".join(text_parts)
        metadata = a2a_msg.get("metadata", {})
        
        # Create appropriate message type
        role = a2a_msg.get("role", "user")
        if role == "user":
            return HumanMessage(content=content, additional_kwargs=metadata)
        elif role == "assistant":
            return AIMessage(content=content, additional_kwargs=metadata)
        elif role == "system":
            return SystemMessage(content=content, additional_kwargs=metadata)
        else:
            # Default to human message
            return HumanMessage(content=content, additional_kwargs=metadata)
            
    def sse_to_a2a_event(self, sse_event: Dict[str, Any]) -> Dict[str, Any]:
        """Convert SSE event to A2A event format.
        
        Args:
            sse_event: SSE event from streaming
            
        Returns:
            A2A compatible event
        """
        event_type = sse_event.get("event_type", "update")
        data = sse_event.get("data", {})
        
        # Map SSE event types to A2A event types
        if event_type == "tokens":
            return {
                "type": "yield",
                "data": {
                    "type": "text",
                    "text": data.get("tokens", "")
                }
            }
        elif event_type == "output":
            return {
                "type": "yield",
                "data": data.get("output")
            }
        elif event_type in ["human_message", "ai_message"]:
            # Handle CurrencyAgent format
            if "content" in data and "is_complete" in data:
                return {
                    "type": "yield",
                    "data": {
                        "type": "text",
                        "text": data.get("content", "")
                    }
                }
            else:
                return {
                    "type": "message",
                    "message": self._convert_message_event_to_a2a(data)
                }
        elif event_type == "intermediate_step":
            return {
                "type": "yield",
                "data": {
                    "type": "text",
                    "text": data.get("content", "")
                }
            }
        elif event_type == "input_required":
            return {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "parts": [{"type": "text", "text": data.get("content", "")}],
                    "metadata": {"require_input": True}
                }
            }
        elif event_type == "error":
            return {
                "type": "error",
                "error": data.get("error", "Unknown error")
            }
        else:
            # Generic event
            return {
                "type": "update",
                "data": data
            }
            
    def _convert_message_event_to_a2a(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert message event data to A2A message format.
        
        Args:
            message_data: Message event data
            
        Returns:
            A2A message
        """
        message_type = message_data.get("type", "HumanMessage")
        content = message_data.get("content", "")
        
        # Determine role from message type
        if "Human" in message_type:
            role = "user"
        elif "AI" in message_type or "Assistant" in message_type:
            role = "assistant"
        elif "System" in message_type:
            role = "system"
        else:
            role = "unknown"
            
        return {
            "role": role,
            "parts": [{"type": "text", "text": content}],
            "metadata": message_data.get("metadata", {})
        }
        
    def task_yield_to_sse(self, yield_update: TaskYieldUpdate) -> Dict[str, Any]:
        """Convert TaskYieldUpdate to SSE event format.
        
        Args:
            yield_update: Task yield update
            
        Returns:
            SSE event data
        """
        return {
            "task_id": yield_update.task_id,
            "event_type": yield_update.event_type,
            "data": yield_update.data,
            "timestamp": yield_update.timestamp.isoformat(),
            "sequence": yield_update.sequence
        }