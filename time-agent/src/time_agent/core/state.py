"""Core state definition for the time agent using LangGraph."""

from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class TimeAgentState(BaseModel):
    """State for the time agent.
    
    This follows LangGraph patterns for state management.
    """
    
    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(
        default_factory=list,
        description="Conversation history with user and assistant messages"
    )
    
    class Config:
        arbitrary_types_allowed = True