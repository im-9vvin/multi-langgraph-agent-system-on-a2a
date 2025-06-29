#!/usr/bin/env python3
"""Test status updates from orchestrator."""

import httpx
import json
import asyncio
import time

async def test_with_polling(query: str):
    """Test orchestrator with task polling to see status updates."""
    print(f"\n🔍 Testing orchestrator with: '{query}'")
    print("-" * 50)
    
    # Create A2A message
    message = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-status-001",
                "role": "user",
                "parts": [{"text": query}],
                "contextId": "test-status"
            }
        },
        "id": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send request
            response = await client.post(
                "http://localhost:10002",
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                task_result = result.get("result", {})
                task_id = task_result.get("id")
                
                if task_id:
                    print(f"Got task ID: {task_id}")
                    print("\nPolling for status updates...")
                    
                    # Poll frequently to catch status updates
                    prev_artifacts = []
                    for i in range(20):
                        await asyncio.sleep(0.5)
                        
                        poll_data = {
                            "jsonrpc": "2.0",
                            "method": "tasks/get",
                            "params": {"id": task_id},
                            "id": i + 2
                        }
                        
                        poll_response = await client.post(
                            "http://localhost:10002",
                            json=poll_data,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if poll_response.status_code == 200:
                            poll_result = poll_response.json()
                            task = poll_result.get("result", {})
                            status = task.get("status", {}).get("state")
                            
                            # Check for status message updates in task status
                            status_obj = task.get("status", {})
                            if isinstance(status_obj, dict) and "message" in status_obj:
                                message = status_obj.get("message", {})
                                if message and "parts" in message:
                                    for part in message.get("parts", []):
                                        if isinstance(part, dict) and "text" in part:
                                            status_text = part["text"]
                                            print(f"[{time.strftime('%H:%M:%S')}] STATUS: {status_text}")
                            
                            # Also check artifacts for backwards compatibility
                            artifacts = task.get("artifacts", [])
                            
                            if status == "completed":
                                print(f"\n✅ Task completed!")
                                # Get final response
                                for artifact in artifacts:
                                    if artifact.get("name") == "response.txt":
                                        for part in artifact.get("parts", []):
                                            if "text" in part:
                                                print(f"\nFinal response:\n{part['text']}")
                                                return
                                break
                            elif status == "failed":
                                print(f"\n❌ Task failed")
                                break
                            
                            # Show progress
                            print(".", end="", flush=True)
                        
                    print("\n⏰ Timeout waiting for completion")
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Test orchestrator with status updates."""
    print("Testing Orchestrator Status Updates")
    print("==================================")
    
    # Test queries
    queries = [
        "원달러 환율 알려줘",
        "지금 몇시야?",
        "100달러는 원화로 얼마야?"
    ]
    
    for query in queries:
        await test_with_polling(query)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())