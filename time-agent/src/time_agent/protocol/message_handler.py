"""Message handling for A2A protocol."""

import json
import logging
from typing import Any, Dict, Optional

from .models import A2AMessage
from .validators import ProtocolValidator

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles A2A protocol message processing."""
    
    @staticmethod
    def create_response(
        message_id: Optional[str],
        result: Any = None,
        error: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a JSON-RPC response.
        
        Args:
            message_id: Original message ID
            result: Result data
            error: Error information
            
        Returns:
            JSON-RPC response dictionary
        """
        response = {
            "jsonrpc": "2.0",
            "id": message_id
        }
        
        if error:
            response["error"] = error
        else:
            response["result"] = result
        
        return response
    
    @staticmethod
    def create_error_response(
        message_id: Optional[str],
        code: int,
        message: str,
        data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Create a JSON-RPC error response.
        
        Args:
            message_id: Original message ID
            code: Error code
            message: Error message
            data: Additional error data
            
        Returns:
            JSON-RPC error response
        """
        error = {
            "code": code,
            "message": message
        }
        
        if data is not None:
            error["data"] = data
        
        return MessageHandler.create_response(message_id, error=error)
    
    @staticmethod
    def parse_message(raw_message: Dict[str, Any]) -> Optional[A2AMessage]:
        """Parse and validate an A2A message.
        
        Args:
            raw_message: Raw message dictionary
            
        Returns:
            Parsed A2AMessage or None if invalid
        """
        is_valid, error = ProtocolValidator.validate_a2a_message(raw_message)
        
        if not is_valid:
            logger.error(f"Invalid message format: {error}")
            return None
        
        try:
            return A2AMessage(**raw_message)
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return None
    
    @staticmethod
    def extract_messages(params: Dict[str, Any]) -> list:
        """Extract messages from A2A params.
        
        Args:
            params: A2A message params
            
        Returns:
            List of messages
        """
        messages = params.get("messages", [])
        
        # Ensure messages is a list
        if not isinstance(messages, list):
            logger.warning("Messages is not a list, wrapping in list")
            messages = [messages]
        
        # Validate message format
        valid_messages = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                valid_messages.append(msg)
            else:
                logger.warning(f"Invalid message format: {msg}")
        
        return valid_messages
    
    @staticmethod
    def format_task_response(task_id: str, status: str) -> Dict[str, Any]:
        """Format a task creation response.
        
        Args:
            task_id: Created task ID
            status: Task status
            
        Returns:
            Formatted response
        """
        return {
            "task": {
                "id": task_id,
                "status": status
            }
        }
    
    @staticmethod
    def format_streaming_event(
        event_type: str,
        data: Any,
        task_id: Optional[str] = None
    ) -> str:
        """Format a streaming event for SSE.
        
        Args:
            event_type: Type of event
            data: Event data
            task_id: Optional task ID
            
        Returns:
            SSE-formatted string
        """
        event = {
            "event": event_type,
            "data": data
        }
        
        if task_id:
            event["task_id"] = task_id
        
        return f"data: {json.dumps(event)}\n\n"