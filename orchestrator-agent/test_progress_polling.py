#!/usr/bin/env python3
"""Test progress updates via task polling."""

import asyncio
import json
import httpx
from datetime import datetime
import time

async def test_progress_polling():
    """Test progress updates by polling task status."""
    url = "http://localhost:10002/"
    
    # Step 1: Send initial message
    send_data = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"text": "현재 환율은 얼마야? USD to KRW로 100달러 환전하면?"}],
                "messageId": f"msg-{int(time.time())}",
                "contextId": "progress-test-001"
            }
        },
        "id": 1
    }
    
    print("1️⃣ Sending initial request...")
    print(f"Request: {json.dumps(send_data, indent=2, ensure_ascii=False)}")
    print("\n" + "="*50 + "\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Send message
        response = await client.post(url, json=send_data)
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return
            
        result = response.json()
        print(f"✅ Response received: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # Extract task ID
        task_id = None
        if "result" in result and "id" in result["result"]:
            task_id = result["result"]["id"]
        elif "result" in result and "task" in result["result"] and "id" in result["result"]["task"]:
            task_id = result["result"]["task"]["id"]
            
        if not task_id:
            print("❌ No task ID found in response")
            return
            
        print(f"\n2️⃣ Task ID: {task_id}")
        print("\n3️⃣ Starting to poll for progress updates...\n")
        
        # Poll for task updates
        poll_count = 0
        max_polls = 20  # Maximum 10 seconds
        last_status = None
        last_message = None
        
        while poll_count < max_polls:
            poll_data = {
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "params": {
                    "id": task_id,
                    "historyLength": 10  # Include recent history
                },
                "id": poll_count + 2
            }
            
            poll_response = await client.post(url, json=poll_data)
            
            if poll_response.status_code == 200:
                poll_result = poll_response.json()
                
                if "result" in poll_result:
                    task = poll_result["result"]
                    status = task.get("status", {})
                    current_status = status.get("state")
                    current_message = status.get("message", "")
                    
                    # Check if status or message changed
                    if current_status != last_status or current_message != last_message:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"[{timestamp}] 📊 Status: {current_status}")
                        
                        if current_message and current_message != last_message:
                            print(f"            💬 {current_message}")
                        
                        last_status = current_status
                        last_message = current_message
                    
                    # Check if task is completed
                    if current_status in ["completed", "failed", "canceled"]:
                        print(f"\n✅ Task {current_status}!")
                        
                        # Print artifacts if available
                        artifacts = task.get("artifacts", [])
                        if artifacts:
                            print("\n📄 Artifacts:")
                            for artifact in artifacts:
                                print(f"   - {artifact.get('name', 'unnamed')}")
                                for part in artifact.get("parts", []):
                                    if part.get("kind") == "text":
                                        print(f"     {part.get('text')}")
                        
                        # Print history if available
                        history = task.get("history", [])
                        if history and len(history) > 1:
                            print("\n📜 Recent History:")
                            for msg in history[-3:]:  # Last 3 messages
                                role = msg.get("role", "unknown")
                                parts = msg.get("parts", [])
                                for part in parts:
                                    if part.get("kind") == "text":
                                        text_preview = part.get("text", "")[:100]
                                        if len(part.get("text", "")) > 100:
                                            text_preview += "..."
                                        print(f"   [{role}] {text_preview}")
                        
                        break
            else:
                print(f"❌ Poll error: {poll_response.status_code}")
            
            poll_count += 1
            await asyncio.sleep(0.5)  # Poll every 500ms
        
        if poll_count >= max_polls:
            print("\n⏱️ Polling timed out")

if __name__ == "__main__":
    print("Testing progress updates via task polling...\n")
    asyncio.run(test_progress_polling())