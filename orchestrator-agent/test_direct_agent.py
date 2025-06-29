#!/usr/bin/env python3
"""Test direct agent calls."""

import httpx
import json
import asyncio

async def test_agent(agent_url, query):
    """Test calling an agent directly."""
    print(f"\n🔍 Testing {agent_url} with: '{query}'")
    print("-" * 50)
    
    # Create A2A message
    message = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-001",
                "role": "user",
                "parts": [{"text": query}],
                "contextId": "test"
            }
        },
        "id": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send request
            response = await client.post(
                agent_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                # Get task ID
                task_result = result.get("result", {})
                task_id = task_result.get("id")
                
                if task_id:
                    print(f"\nPolling task {task_id}...")
                    
                    # Poll once
                    await asyncio.sleep(2)
                    
                    poll_data = {
                        "jsonrpc": "2.0",
                        "method": "tasks/get",
                        "params": {"id": task_id},
                        "id": 2
                    }
                    
                    poll_response = await client.post(
                        agent_url,
                        json=poll_data,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if poll_response.status_code == 200:
                        poll_result = poll_response.json()
                        task = poll_result.get("result", {})
                        
                        # Extract response
                        artifacts = task.get("artifacts", [])
                        for artifact in artifacts:
                            if "parts" in artifact:
                                for part in artifact["parts"]:
                                    if "text" in part:
                                        print(f"\n✅ Agent response: {part['text']}")
                                        return part["text"]
                        
                        print("\n❌ No response in task")
                    else:
                        print(f"\n❌ Poll failed: {poll_response.status_code}")
            else:
                print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        
    return None

async def main():
    """Test both agents."""
    print("Testing Direct Agent Calls")
    print("=========================")
    
    # Test Currency Agent
    await test_agent("http://localhost:10000", "원달러 환율 알려줘")
    
    # Test Time Agent
    await test_agent("http://localhost:10001", "지금 몇시야?")

if __name__ == "__main__":
    asyncio.run(main())