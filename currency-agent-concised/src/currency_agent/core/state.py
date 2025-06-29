# Type annotations
from typing import Literal

# Third-party imports
from pydantic import BaseModel


class ResponseFormat(BaseModel):
    """
    Agent response format definition for structured outputs.
    
    This model ensures consistent response formatting that clients
    can reliably parse.
    
    Attributes:
        status: Response status indicating the agent's state
            - 'input_required': User needs to provide more information
            - 'completed': Request successfully completed
            - 'error': Error occurred during processing
        message: Human-readable message content
    """
    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str