"""Message handler for A2A JSON-RPC protocol."""

import json
import logging
from typing import Any, Dict, Optional, Callable, Tuple, Union

from .models import A2AMessage
from .validators import ProtocolValidator
from ..common.exceptions import ProtocolError


logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles A2A JSON-RPC message processing."""
    
    def __init__(self):
        """Initialize message handler."""
        self.method_handlers: Dict[str, Callable] = {}
        self.validator = ProtocolValidator()
        
    def register_method(self, method: str, handler: Callable) -> None:
        """Register a method handler.
        
        Args:
            method: JSON-RPC method name
            handler: Async handler function
        """
        self.method_handlers[method] = handler
        logger.debug(f"Registered handler for method: {method}")
        
    async def handle_message(self, raw_message: str) -> Optional[Dict[str, Any]]:
        """Process incoming JSON-RPC message.
        
        Args:
            raw_message: Raw JSON-RPC message string
            
        Returns:
            Response data or None
            
        Raises:
            ProtocolError: If message is invalid
        """
        try:
            # Parse message
            data = json.loads(raw_message)
        except json.JSONDecodeError as e:
            raise ProtocolError(f"Invalid JSON: {e}")
            
        # Validate message format
        is_valid, error = self.validator.validate_jsonrpc_message(data)
        if not is_valid:
            raise ProtocolError(f"Invalid message format: {error}")
            
        # Create message object
        message = A2AMessage(**data)
        
        # Check if method is supported
        if message.method not in self.method_handlers:
            return self._create_error_response(
                message.id,
                -32601,
                f"Method not found: {message.method}"
            )
            
        # Execute handler
        try:
            handler = self.method_handlers[message.method]
            result = await handler(message.params)
            
            # Return response if request had an ID
            if message.id is not None:
                return self._create_success_response(message.id, result)
                
            return None  # Notification, no response
            
        except Exception as e:
            logger.error(f"Handler error for {message.method}: {e}")
            if message.id is not None:
                return self._create_error_response(
                    message.id,
                    -32603,
                    f"Internal error: {str(e)}"
                )
            return None
    
    def _create_success_response(self, 
                                request_id: Optional[Union[str, int]], 
                                result: Any) -> Dict[str, Any]:
        """Create JSON-RPC success response.
        
        Args:
            request_id: Request ID
            result: Response result
            
        Returns:
            Response dictionary
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    
    def _create_error_response(self,
                             request_id: Optional[Union[str, int]],
                             code: int,
                             message: str,
                             data: Optional[Any] = None) -> Dict[str, Any]:
        """Create JSON-RPC error response.
        
        Args:
            request_id: Request ID
            code: Error code
            message: Error message
            data: Optional error data
            
        Returns:
            Error response dictionary
        """
        error = {
            "code": code,
            "message": message
        }
        
        if data is not None:
            error["data"] = data
            
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error
        }
    
    def create_notification(self, method: str, params: Dict[str, Any]) -> str:
        """Create JSON-RPC notification message.
        
        Args:
            method: Method name
            params: Method parameters
            
        Returns:
            JSON string
        """
        message = A2AMessage(
            method=method,
            params=params
        )
        return json.dumps(message.model_dump(exclude_none=True))
    
    def create_request(self, 
                      method: str, 
                      params: Dict[str, Any],
                      request_id: Union[str, int]) -> str:
        """Create JSON-RPC request message.
        
        Args:
            method: Method name
            params: Method parameters
            request_id: Request ID
            
        Returns:
            JSON string
        """
        message = A2AMessage(
            method=method,
            params=params,
            id=request_id
        )
        return json.dumps(message.model_dump())