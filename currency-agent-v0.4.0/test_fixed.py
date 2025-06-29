#!/usr/bin/env python3
"""Test the fixed v0.4.0 implementation."""

import httpx
import json
import time

print("Currency Agent v0.4.0 - Fixed Response Test")
print("==========================================")
print("Make sure the server is running: uv run currency-agent")
print()

# Test message
data = {
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "messageId": "test-fixed-001",
            "role": "user",
            "parts": [
                {"text": "What is the exchange rate from USD to EUR?"}
            ],
            "contextId": "test-fixed"
        }
    },
    "id": 1
}

try:
    print("Sending request...")
    response = httpx.post(
        "http://localhost:10000/",
        json=data,
        headers={"Content-Type": "application/json"},
        timeout=30.0
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        # Get task ID for polling
        if "result" in result:
            task_result = result["result"]
            task_id = task_result.get("id")
            initial_status = task_result.get("status", {}).get("state", "unknown")
            print(f"Task ID: {task_id}")
            print(f"Initial status: {initial_status}")
            
            # If already completed, check for artifact
            if initial_status == "completed" and "artifact" in task_result and task_result["artifact"]:
                artifact = task_result["artifact"]
                print("\n✅ SUCCESS! Got response:")
                print("=" * 50)
                if "parts" in artifact:
                    for part in artifact["parts"]:
                        if isinstance(part, dict) and "text" in part:
                            print(part["text"])
                print("=" * 50)
            else:
                # Poll for completion
                print("\nWaiting for response...")
                poll_data = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {"id": task_id},
                    "id": 2
                }
                
                for i in range(10):  # Try for 10 seconds
                    time.sleep(1)
                    poll_response = httpx.post(
                        "http://localhost:10000/",
                        json=poll_data,
                        headers={"Content-Type": "application/json"},
                        timeout=30.0
                    )
                    
                    if poll_response.status_code == 200:
                        poll_result = poll_response.json()
                        task = poll_result.get("result", {})
                        status = task.get("status", {}).get("state", "unknown")
                        
                        if status == "completed":
                            if "artifact" in task and task["artifact"]:
                                artifact = task["artifact"]
                                print("\n✅ SUCCESS! Got response:")
                                print("=" * 50)
                                if "parts" in artifact:
                                    for part in artifact["parts"]:
                                        if "text" in part:
                                            print(part["text"])
                                print("=" * 50)
                            else:
                                print("\n❌ Task completed but no artifact")
                            break
                        elif status == "failed":
                            print("\n❌ Task failed")
                            break
                        else:
                            print(f"  Status: {status}")
                else:
                    print("\n❌ Timeout waiting for response")
    else:
        print(f"Error response: {response.text}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nMake sure the server is running: uv run currency-agent")