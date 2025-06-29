"""Test client for the orchestrator agent."""

import asyncio
import json
import time
from typing import Any, Dict

import httpx


class OrchestratorTestClient:
    """Test client for orchestrator agent."""
    
    def __init__(self, base_url: str = "http://localhost:10002"):
        self.base_url = base_url
    
    async def send_message(self, message: str, context_id: str = "test") -> Dict[str, Any]:
        """Send a message to the orchestrator."""
        request = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": f"test-{int(time.time())}",
                    "role": "user",
                    "parts": [{"text": message}],
                    "contextId": context_id
                }
            },
            "id": 1
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/message",
                json=request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/tasks/{task_id}")
            response.raise_for_status()
            return response.json()
    
    async def wait_for_completion(
        self, 
        task_id: str, 
        max_polls: int = 30,
        poll_interval: float = 1.0
    ) -> Dict[str, Any]:
        """Wait for task to complete."""
        for i in range(max_polls):
            task = await self.get_task(task_id)
            
            if task["status"] in ["completed", "failed", "cancelled"]:
                return task
            
            print(f"Task {task_id} status: {task['status']}")
            
            if i < max_polls - 1:
                await asyncio.sleep(poll_interval)
        
        raise TimeoutError(f"Task {task_id} did not complete in time")
    
    async def get_agent_card(self) -> Dict[str, Any]:
        """Get agent card."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/.well-known/agent.json")
            response.raise_for_status()
            return response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check agent health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()


async def test_orchestration():
    """Test the orchestrator agent."""
    client = OrchestratorTestClient()
    
    print("🔍 Checking orchestrator health...")
    health = await client.health_check()
    print(f"✅ Health: {health}")
    
    print("\n📋 Getting agent card...")
    card = await client.get_agent_card()
    print(f"✅ Agent: {card['name']} v{card['version']}")
    print(f"   Capabilities: {', '.join(card['capabilities'])}")
    print(f"   Remote agents: {card['orchestration']['remote_agents']}")
    
    # Test cases
    test_cases = [
        "What is the current USD to EUR exchange rate?",
        "Tell me about Python programming language",
        "What is the USD to EUR rate and also tell me about Python?",
        "Convert 100 USD to EUR and explain what REST APIs are"
    ]
    
    for test_message in test_cases:
        print(f"\n🚀 Testing: {test_message}")
        
        try:
            # Send message
            response = await client.send_message(test_message)
            task_id = response["result"]["taskId"]
            print(f"📝 Task created: {task_id}")
            
            # Wait for completion
            completed_task = await client.wait_for_completion(task_id)
            print(f"✅ Task completed with status: {completed_task['status']}")
            
            # Extract results
            if completed_task["status"] == "completed":
                if "result" in completed_task and "artifacts" in completed_task["result"]:
                    artifacts = completed_task["result"]["artifacts"]
                    print("\n📄 Results:")
                    for artifact in artifacts:
                        if artifact.get("mimeType") == "text/plain":
                            print(artifact.get("data", ""))
                else:
                    print("No artifacts in response")
            else:
                print(f"❌ Task failed: {completed_task.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 80)


if __name__ == "__main__":
    print("🤖 Orchestrator Agent Test Client")
    print("=" * 80)
    
    asyncio.run(test_orchestration())