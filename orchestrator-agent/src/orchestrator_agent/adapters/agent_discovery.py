"""Dynamic agent discovery for A2A orchestration."""

import httpx
from typing import Dict, List, Optional, Any
import asyncio
from ..common import get_logger

logger = get_logger(__name__)


class AgentRegistry:
    """Registry for dynamically discovered A2A agents."""
    
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.httpx_client = httpx.AsyncClient(timeout=10.0)
        
    async def discover_agent(self, agent_url: str) -> Optional[Dict[str, Any]]:
        """
        Discover an agent by fetching its agent card.
        
        Args:
            agent_url: Base URL of the agent
            
        Returns:
            Agent card if successful, None otherwise
        """
        try:
            # Fetch agent card
            response = await self.httpx_client.get(
                f"{agent_url}/.well-known/agent.json"
            )
            
            if response.status_code == 200:
                agent_card = response.json()
                
                # Validate basic structure
                if "name" in agent_card and "capabilities" in agent_card:
                    self.agents[agent_url] = {
                        "url": agent_url,
                        "card": agent_card,
                        "name": agent_card["name"],
                        "description": agent_card.get("description", ""),
                        "capabilities": agent_card["capabilities"],
                        "skills": agent_card.get("skills", [])
                    }
                    
                    logger.info(f"Discovered agent: {agent_card['name']} at {agent_url}")
                    return agent_card
                    
        except Exception as e:
            logger.error(f"Failed to discover agent at {agent_url}: {e}")
            
        return None
    
    async def discover_multiple(self, agent_urls: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Discover multiple agents concurrently.
        
        Args:
            agent_urls: List of agent URLs to discover
            
        Returns:
            Dictionary of discovered agents
        """
        tasks = [self.discover_agent(url) for url in agent_urls]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self.agents
    
    def find_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Find agents that have a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of agents with that capability
        """
        matching_agents = []
        
        for agent_info in self.agents.values():
            capabilities = agent_info.get("capabilities", {})
            
            # Check if capability exists in any form
            if capability in capabilities:
                matching_agents.append(agent_info)
            elif "skills" in agent_info:
                # Check skills for capability
                for skill in agent_info["skills"]:
                    if capability.lower() in skill.get("name", "").lower():
                        matching_agents.append(agent_info)
                        break
                        
        return matching_agents
    
    def get_agent_summary(self) -> str:
        """Get a summary of all discovered agents for LLM context."""
        summary = []
        
        for url, info in self.agents.items():
            agent_desc = f"- {info['name']} ({url}): {info['description']}"
            
            # Add capabilities
            if info.get("skills"):
                skills = [s.get("name", "") for s in info["skills"]]
                agent_desc += f"\n  Skills: {', '.join(skills)}"
                
            summary.append(agent_desc)
            
        return "\n".join(summary) if summary else "No agents discovered yet."
    
    async def close(self):
        """Close HTTP client."""
        await self.httpx_client.aclose()


# Global registry instance
agent_registry = AgentRegistry()