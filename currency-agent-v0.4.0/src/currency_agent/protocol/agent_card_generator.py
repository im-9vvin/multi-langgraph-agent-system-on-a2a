"""Agent card generator for A2A discovery."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from .models import AgentCard


class AgentCardGenerator:
    """Generates and manages A2A agent discovery cards."""
    
    def __init__(self, agent_name: str, version: str, base_url: str):
        """Initialize agent card generator.
        
        Args:
            agent_name: Name of the agent
            version: Agent version
            base_url: Base URL where agent is hosted
        """
        self.agent_name = agent_name
        self.version = version
        self.base_url = base_url.rstrip('/')
        
    def generate_card(self, 
                     description: str,
                     capabilities: list[str],
                     authentication: Optional[Dict[str, Any]] = None) -> AgentCard:
        """Generate agent discovery card.
        
        Args:
            description: Agent description
            capabilities: List of agent capabilities
            authentication: Optional auth configuration
            
        Returns:
            AgentCard instance
        """
        return AgentCard(
            name=self.agent_name,
            description=description,
            version=self.version,
            capabilities=capabilities,
            endpoints={
                "message": f"{self.base_url}/message",
                "stream": f"{self.base_url}/message/stream",
                "tasks": f"{self.base_url}/tasks",
                "health": f"{self.base_url}/health",
                "discovery": f"{self.base_url}/.well-known/agent.json"
            },
            authentication=authentication,
            metadata={
                "protocol_version": "1.0",
                "langgraph_enabled": True,
                "streaming_supported": True
            }
        )
    
    def save_card(self, card: AgentCard, output_path: Path) -> None:
        """Save agent card to file.
        
        Args:
            card: AgentCard to save
            output_path: Path to save the card
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(card.model_dump(), f, indent=2)
            
    def load_card(self, card_path: Path) -> AgentCard:
        """Load agent card from file.
        
        Args:
            card_path: Path to agent card file
            
        Returns:
            Loaded AgentCard instance
        """
        with open(card_path, 'r') as f:
            data = json.load(f)
        return AgentCard(**data)