#!/usr/bin/env python
"""Test client for the time agent."""

import asyncio
import json
import sys
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel


class A2AMessage(BaseModel):
    """A2A protocol message."""
    jsonrpc: str = "2.0"
    method: str = "message"
    params: Dict[str, Any]
    id: Optional[str] = "1"


class TimeAgentClient:
    """Test client for interacting with the time agent."""
    
    def __init__(self, base_url: str = "http://localhost:10001"):
        """Initialize client.
        
        Args:
            base_url: Base URL of the time agent server
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def send_message(self, content: str) -> Dict[str, Any]:
        """Send a message to the agent.
        
        Args:
            content: Message content
            
        Returns:
            Response data
        """
        message = A2AMessage(
            jsonrpc="2.0",
            method="message",
            params={
                "messages": [
                    {"role": "user", "content": content}
                ]
            },
            id="1"
        )
        
        response = await self.client.post(
            f"{self.base_url}/message/send",
            json=message.model_dump()
        )
        
        response.raise_for_status()
        return response.json()
    
    async def poll_task(self, task_id: str, max_attempts: int = 30) -> Dict[str, Any]:
        """Poll for task completion.
        
        Args:
            task_id: Task ID to poll
            max_attempts: Maximum polling attempts
            
        Returns:
            Final task data
        """
        for attempt in range(max_attempts):
            response = await self.client.get(f"{self.base_url}/tasks/{task_id}")
            
            if response.status_code == 200:
                task_data = response.json()
                
                if task_data.get("status") in ["completed", "failed"]:
                    return task_data
            
            # Wait before next poll
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Task {task_id} did not complete within timeout")
    
    async def get_health(self) -> Dict[str, Any]:
        """Get server health status.
        
        Returns:
            Health data
        """
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """Get agent discovery information.
        
        Returns:
            Agent metadata
        """
        response = await self.client.get(f"{self.base_url}/.well-known/agent.json")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()


async def test_time_queries():
    """Test various time queries."""
    client = TimeAgentClient()
    
    try:
        # Test health check
        print("=== Health Check ===")
        health = await client.get_health()
        print(json.dumps(health, indent=2))
        print()
        
        # Test agent info
        print("=== Agent Info ===")
        info = await client.get_agent_info()
        print(json.dumps(info, indent=2))
        print()
        
        # Test queries
        queries = [
            "What time is it in Tokyo?",
            "What's the current time in New York?",
            "Convert 3:30 PM EST to London time",
            "What time is 14:00 in Paris when converted to Singapore?",
            "Show me the time difference between Los Angeles and Sydney"
        ]
        
        for query in queries:
            print(f"=== Query: {query} ===")
            
            # Send message
            response = await client.send_message(query)
            print(f"Initial response: {json.dumps(response, indent=2)}")
            
            # Extract task ID
            task_id = response.get("result", {}).get("task", {}).get("id")
            if task_id:
                print(f"Task ID: {task_id}")
                
                # Poll for completion
                print("Polling for completion...")
                final_task = await client.poll_task(task_id)
                
                print(f"Final status: {final_task.get('status')}")
                
                if final_task.get('output_data'):
                    print("Response:")
                    print(final_task['output_data'].get('response', 'No response'))
                
                if final_task.get('error'):
                    print(f"Error: {final_task['error']}")
            
            print("\n" + "="*50 + "\n")
            
            # Small delay between queries
            await asyncio.sleep(1)
    
    finally:
        await client.close()


def main():
    """Run the test client."""
    try:
        asyncio.run(test_time_queries())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()