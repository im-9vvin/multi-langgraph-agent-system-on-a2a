#!/usr/bin/env python
"""Test the time agent server."""

import httpx
import json
import time


def test_health():
    """Test health endpoint."""
    try:
        response = httpx.get("http://localhost:10001/health")
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")


def test_agent_discovery():
    """Test agent discovery endpoint."""
    try:
        response = httpx.get("http://localhost:10001/.well-known/agent.json")
        print(f"\nAgent discovery: {response.status_code}")
        if response.status_code == 200:
            print(f"Agent info: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Agent discovery failed: {e}")


def test_a2a_message():
    """Test A2A message endpoint."""
    message = {
        "jsonrpc": "2.0",
        "method": "message",
        "params": {
            "messages": [
                {"role": "user", "content": "What time is it in Tokyo?"}
            ]
        },
        "id": "test-1"
    }
    
    try:
        # Send message
        response = httpx.post("http://localhost:10001/message", json=message, timeout=30.0)
        print(f"\nA2A message: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # If we got a task ID, poll for the result
        if "result" in result and "task_id" in result["result"]:
            task_id = result["result"]["task_id"]
            print(f"\nPolling task {task_id}...")
            
            # Poll for completion
            for i in range(10):
                time.sleep(2)
                task_response = httpx.get(f"http://localhost:10001/tasks/{task_id}")
                if task_response.status_code == 200:
                    task_data = task_response.json()
                    print(f"Task status: {task_data.get('status')}")
                    
                    if task_data.get("status") == "completed":
                        print(f"Task completed!")
                        if "artifacts" in task_data:
                            print(f"Artifacts: {json.dumps(task_data['artifacts'], indent=2)}")
                        break
                else:
                    print(f"Task query failed: {task_response.status_code}")
    except Exception as e:
        print(f"A2A message failed: {e}")


if __name__ == "__main__":
    print("Testing Time Agent server at http://localhost:10001")
    test_health()
    test_agent_discovery()
    test_a2a_message()