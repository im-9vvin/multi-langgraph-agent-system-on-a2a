#!/usr/bin/env python3
"""Test time agent response format."""
import httpx
import json
import time

def test_time_agent():
    """Test time agent A2A response format."""
    print("Time Agent Response Format Test")
    print("="*50)
    
    # Send A2A message
    data = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-001",
                "role": "user",
                "parts": [{"text": "What time is it in Seoul?"}],
                "contextId": "test"
            }
        },
        "id": 1
    }
    
    print("Sending request...")
    response = httpx.post(
        "http://localhost:10001/",
        json=data,
        headers={"Content-Type": "application/json"},
        timeout=30.0
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    task_id = result.get("result", {}).get("id")
    print(f"Task ID: {task_id}")
    
    # Poll for completion
    print("\nPolling for completion...")
    poll_data = {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "params": {"id": task_id},
        "id": 2
    }
    
    for i in range(10):
        time.sleep(1)
        poll_response = httpx.post(
            "http://localhost:10001/",
            json=poll_data,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        
        if poll_response.status_code == 200:
            poll_result = poll_response.json()
            print(f"\nPoll result:\n{json.dumps(poll_result, indent=2)}")
            
            task_data = poll_result.get("result", {})
            status = task_data.get("status", {}).get("state")
            
            if status == "completed":
                print("\n✅ Task completed!")
                break
            elif status == "failed":
                print("\n❌ Task failed!")
                break

if __name__ == "__main__":
    test_time_agent()