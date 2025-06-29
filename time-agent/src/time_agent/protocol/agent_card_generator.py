"""Agent card generator for A2A discovery."""

from typing import Dict, List


class AgentCardGenerator:
    """Generates agent discovery metadata for A2A protocol."""
    
    @staticmethod
    def generate() -> Dict[str, any]:
        """Generate agent card for discovery.
        
        Returns:
            Agent metadata dictionary
        """
        return {
            "name": "Time Agent",
            "version": "1.0.0",
            "description": "An intelligent time and timezone assistant that provides current time information and timezone conversions",
            "capabilities": [
                "current_time",
                "timezone_conversion",
                "timezone_information"
            ],
            "supported_protocols": ["a2a/0.2"],
            "endpoints": {
                "message": "/message/send",
                "stream": "/message/stream",
                "tasks": "/tasks",
                "health": "/health"
            },
            "metadata": {
                "model": "gpt-4o-mini",
                "framework": "langgraph",
                "features": [
                    "streaming",
                    "checkpointing",
                    "task_management"
                ],
                "timezones": {
                    "supported": "All IANA timezones",
                    "common_aliases": [
                        "EST", "PST", "GMT", "BST", 
                        "JST", "CST", "MST"
                    ]
                }
            },
            "examples": [
                {
                    "input": "What time is it in Tokyo?",
                    "output": "The current time in Tokyo (JST) is 14:30:45"
                },
                {
                    "input": "Convert 3:30 PM EST to London time",
                    "output": "3:30 PM EST is 8:30 PM GMT in London"
                }
            ],
            "rate_limits": {
                "requests_per_minute": 60,
                "concurrent_tasks": 10
            },
            "authentication": {
                "required": False,
                "methods": ["bearer_token"]
            }
        }
    
    @staticmethod
    def generate_health_info() -> Dict[str, any]:
        """Generate health check information.
        
        Returns:
            Health status dictionary
        """
        return {
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "agent": "running",
                "mcp_time_server": "connected",
                "task_manager": "operational"
            },
            "uptime_seconds": 0,  # Would be calculated in real implementation
            "tasks": {
                "active": 0,
                "completed": 0,
                "failed": 0
            }
        }