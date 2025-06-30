#!/usr/bin/env python3
"""Test script to verify Hotel Agent (AGENT_3) is properly registered and working."""

import asyncio
import httpx
import json
import sys

async def test_hotel_agent():
    """Test hotel agent routing through orchestrator."""
    orchestrator_url = "http://localhost:10002"
    
    # Test message that should route to hotel agent
    test_message = "서울의 좋은 호텔을 추천해줘"
    
    print(f"Testing orchestrator with message: '{test_message}'")
    print(f"Orchestrator URL: {orchestrator_url}")
    print("-" * 50)
    
    # Create A2A message
    a2a_message = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-hotel-001",
                "role": "user",
                "parts": [{"text": test_message}],
                "contextId": "test-hotel"
            }
        },
        "id": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Send message to orchestrator
            print("Sending message to orchestrator...")
            response = await client.post(
                orchestrator_url,
                json=a2a_message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("result", {}).get("id")
                print(f"Got task ID: {task_id}")
                
                if task_id:
                    # Poll for completion
                    print("\nPolling for task completion...")
                    for i in range(30):  # Poll for up to 30 seconds
                        await asyncio.sleep(2.0)
                        
                        poll_data = {
                            "jsonrpc": "2.0",
                            "method": "tasks/get",
                            "params": {"id": task_id},
                            "id": 2
                        }
                        
                        poll_response = await client.post(
                            orchestrator_url,
                            json=poll_data,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if poll_response.status_code == 200:
                            poll_result = poll_response.json()
                            task_data = poll_result.get("result", {})
                            status = task_data.get("status", {}).get("state")
                            
                            print(f"Status: {status}")
                            
                            if status == "completed":
                                # Extract result
                                print("\nTask completed successfully!")
                                print("\nFull response:")
                                print(json.dumps(task_data, indent=2, ensure_ascii=False))
                                
                                # Extract text from artifacts
                                artifacts = task_data.get("artifacts", [])
                                for artifact in artifacts:
                                    if "parts" in artifact:
                                        for part in artifact["parts"]:
                                            if isinstance(part, dict) and part.get("kind") == "text":
                                                print("\nOrchestrator response:")
                                                print(part.get("text", ""))
                                return True
                                
                            elif status == "failed":
                                print("\nTask failed!")
                                print(json.dumps(task_data, indent=2, ensure_ascii=False))
                                return False
                        else:
                            print(f"Poll request failed: {poll_response.status_code}")
                            return False
                    
                    print("\nTask timed out after 30 seconds")
                    return False
                else:
                    print("No task ID returned")
                    return False
            else:
                print(f"Initial request failed: {response.status_code}")
                print(response.text)
                return False
                
    except Exception as e:
        print(f"Error: {e}")
        return False

async def check_orchestrator_health():
    """Check if orchestrator is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:10002/.well-known/agent.json")
            if response.status_code == 200:
                print("✓ Orchestrator is running")
                return True
            else:
                print("✗ Orchestrator returned status:", response.status_code)
                return False
    except Exception as e:
        print("✗ Orchestrator is not running:", str(e))
        return False

async def main():
    """Run the test."""
    print("Hotel Agent (AGENT_3) Registration Test")
    print("=" * 50)
    
    # Check if orchestrator is running
    if not await check_orchestrator_health():
        print("\nPlease start the orchestrator first:")
        print("cd /home/march/workbench/im-9vvin/multi-langgraph-agent-system-on-a2a/orchestrator-agent")
        print("uv run python -m orchestrator_agent.server")
        sys.exit(1)
    
    print()
    
    # Run the test
    success = await test_hotel_agent()
    
    if success:
        print("\n✓ Hotel Agent is properly registered and working!")
    else:
        print("\n✗ Hotel Agent test failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())