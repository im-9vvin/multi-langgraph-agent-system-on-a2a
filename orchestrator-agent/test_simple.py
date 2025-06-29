#!/usr/bin/env python3
"""Simple test for orchestrator."""

import httpx
import json
import time
import sys

def test_query(query):
    print(f"\n🔍 Testing: '{query}'")
    print("-" * 50)
    
    # Create message
    data = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": f"test-{int(time.time())}",
                "role": "user",
                "parts": [{"text": query}],
                "contextId": "test-simple"
            }
        },
        "id": 1
    }
    
    try:
        # Send request
        print("Sending request to orchestrator...")
        response = httpx.post(
            "http://localhost:10002/",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=10.0
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # Get task ID
            if "result" in result:
                task_id = result["result"].get("id")
                print(f"\nTask ID: {task_id}")
                
                # Wait a bit
                print("\nWaiting 2 seconds before polling...")
                time.sleep(2)
                
                # Poll once
                poll_data = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {"id": task_id},
                    "id": 2
                }
                
                print("\nPolling for task status...")
                poll_response = httpx.post(
                    "http://localhost:10002/",
                    json=poll_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
                
                if poll_response.status_code == 200:
                    poll_result = poll_response.json()
                    print(f"Poll response: {json.dumps(poll_result, indent=2, ensure_ascii=False)}")
                else:
                    print(f"Poll failed: {poll_response.status_code} - {poll_response.text}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "안녕하세요"
    
    test_query(query)