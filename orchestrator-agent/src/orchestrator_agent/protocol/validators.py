"""Validators for A2A protocol compliance."""

from typing import Any

from ..common.exceptions import ProtocolError


def validate_a2a_message(message: dict[str, Any]) -> None:
    """Validate A2A message structure."""
    required_fields = ["messageId", "role", "parts"]
    
    for field in required_fields:
        if field not in message:
            raise ProtocolError(f"Missing required field: {field}")
    
    # Validate role
    if message["role"] not in ["user", "assistant"]:
        raise ProtocolError(f"Invalid role: {message['role']}")
    
    # Validate parts
    if not isinstance(message["parts"], list):
        raise ProtocolError("Parts must be a list")
    
    if not message["parts"]:
        raise ProtocolError("Parts cannot be empty")
    
    # Validate each part
    for part in message["parts"]:
        if not isinstance(part, dict):
            raise ProtocolError("Each part must be a dictionary")
        
        # At least one of text, data, or mimeType should be present
        if not any(key in part for key in ["text", "data", "mimeType"]):
            raise ProtocolError("Part must contain text, data, or mimeType")