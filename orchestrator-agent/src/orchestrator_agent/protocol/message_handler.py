"""Message handling for A2A protocol."""

import json
from typing import Any, Dict, Optional

from ..common import get_logger
from ..common.exceptions import ProtocolError
from .models import A2AMessage
from .validators import validate_a2a_message

logger = get_logger(__name__)


class MessageHandler:
    """Handles A2A protocol messages."""
    
    @staticmethod
    def parse_jsonrpc_request(request_data: dict) -> tuple[str, dict, Any]:
        """Parse JSON-RPC request.
        
        Returns:
            Tuple of (method, params, id)
        """
        if "jsonrpc" not in request_data or request_data["jsonrpc"] != "2.0":
            raise ProtocolError("Invalid JSON-RPC version")
        
        method = request_data.get("method")
        if not method:
            raise ProtocolError("Missing method in JSON-RPC request")
        
        params = request_data.get("params", {})
        request_id = request_data.get("id")
        
        return method, params, request_id
    
    @staticmethod
    def create_jsonrpc_response(result: Any, request_id: Any) -> dict:
        """Create JSON-RPC response."""
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
    
    @staticmethod
    def create_jsonrpc_error(error_message: str, error_code: int, request_id: Any) -> dict:
        """Create JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": error_code,
                "message": error_message
            },
            "id": request_id
        }
    
    @staticmethod
    def extract_a2a_message(params: dict) -> A2AMessage:
        """Extract and validate A2A message from params."""
        message_data = params.get("message")
        if not message_data:
            raise ProtocolError("Missing message in params")
        
        # Validate message structure
        validate_a2a_message(message_data)
        
        # Create A2A message object
        return A2AMessage(**message_data)
    
    @staticmethod
    def format_task_response(task_id: str, status: str, context_id: Optional[str] = None) -> dict:
        """Format task creation response in A2A protocol format."""
        # Create task object matching A2A protocol
        task = {
            "id": task_id,
            "contextId": context_id or f"ctx-{task_id}",
            "status": {
                "state": status,
                "final": status in ["completed", "failed", "cancelled"]
            }
        }
        
        return {
            "task": task
        }