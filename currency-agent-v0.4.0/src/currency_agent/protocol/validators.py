"""Protocol validation utilities for A2A messages."""

from typing import Any, Dict, Optional, Tuple
from .models import A2AMessage, TaskStatus


class ProtocolValidator:
    """Validates A2A protocol messages and data."""
    
    @staticmethod
    def validate_jsonrpc_message(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate JSON-RPC 2.0 message format.
        
        Args:
            data: Raw message data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(data, dict):
            return False, "Message must be a JSON object"
            
        if data.get('jsonrpc') != '2.0':
            return False, "Invalid JSON-RPC version"
            
        if 'method' not in data:
            return False, "Missing required field: method"
            
        if not isinstance(data.get('method'), str):
            return False, "Method must be a string"
            
        if 'params' in data and not isinstance(data['params'], dict):
            return False, "Params must be an object"
            
        return True, None
    
    @staticmethod
    def validate_task_input(input_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate task input data.
        
        Args:
            input_data: Task input parameters
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Add specific validation for currency agent tasks
        if 'amount' in input_data:
            if not isinstance(input_data['amount'], (int, float)):
                return False, "Amount must be a number"
            if input_data['amount'] <= 0:
                return False, "Amount must be positive"
                
        if 'from_currency' in input_data:
            if not isinstance(input_data['from_currency'], str):
                return False, "from_currency must be a string"
            if len(input_data['from_currency']) != 3:
                return False, "from_currency must be a 3-letter code"
                
        if 'to_currency' in input_data:
            if not isinstance(input_data['to_currency'], str):
                return False, "to_currency must be a string"
            if len(input_data['to_currency']) != 3:
                return False, "to_currency must be a 3-letter code"
                
        return True, None
    
    @staticmethod
    def validate_task_status(status: str) -> bool:
        """Check if task status is valid."""
        try:
            TaskStatus(status)
            return True
        except ValueError:
            return False