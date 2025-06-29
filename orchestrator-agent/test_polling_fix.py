#!/usr/bin/env python3
"""Test the fixed polling implementation."""

import httpx
import json
import time
import asyncio

async def test_orchestrator():
    print("Orchestrator Agent - Polling Fix Test")
    print("=====================================")
    print("Make sure all servers are running:")
    print("- Currency agent on localhost:10000")
    print("- General agent on localhost:10001")
    print("- Orchestrator on localhost:10002")
    print()
    
    # Test queries
    test_queries = [
        "원달러 환율 알려줘",
        "지금 몇시야?",
        "안녕하세요",
        "뭘 해줄 수 있어?"
    ]
    
    for query in test_queries:
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
                    "contextId": "test-polling"
                }
            },
            "id": 1
        }
        
        try:
            # Send request
            async with httpx.AsyncClient(timeout=60.0) as client:
                print("Sending request...")
                response = await client.post(
                    "http://localhost:10002/",
                    json=data,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Get task ID
                    if "result" in result:
                        task_result = result["result"]
                        task_id = task_result.get("id")
                        print(f"Task ID: {task_id}")
                        
                        # Poll for completion using JSON-RPC
                        for attempt in range(15):  # 15 seconds max
                            await asyncio.sleep(1)
                            
                            poll_data = {
                                "jsonrpc": "2.0",
                                "method": "tasks/get",
                                "params": {"id": task_id},
                                "id": 2
                            }
                            
                            poll_response = await client.post(
                                "http://localhost:10002/",
                                json=poll_data,
                                headers={"Content-Type": "application/json"}
                            )
                            
                            if poll_response.status_code == 200:
                                poll_result = poll_response.json()
                                task = poll_result.get("result", {})
                                status = task.get("status", {}).get("state", "unknown")
                                
                                print(f"  Attempt {attempt + 1}: {status}")
                                
                                if status == "completed":
                                    # Get artifact
                                    if "artifact" in task and task["artifact"]:
                                        artifact = task["artifact"]
                                        print("\n✅ Response:")
                                        print("=" * 50)
                                        if "parts" in artifact:
                                            for part in artifact["parts"]:
                                                if isinstance(part, dict) and "text" in part:
                                                    print(part["text"])
                                        print("=" * 50)
                                    else:
                                        print("\n❌ Task completed but no artifact")
                                    break
                                elif status == "failed":
                                    print("\n❌ Task failed")
                                    break
                        else:
                            print("\n❌ Timeout waiting for response")
                else:
                    print(f"Error: {response.text}")
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\nMake sure all servers are running!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())