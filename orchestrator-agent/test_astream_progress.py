#!/usr/bin/env python3
"""Test LangGraph astream progress updates."""

import asyncio
import json
import httpx
from datetime import datetime
import time

async def monitor_task_progress(client: httpx.AsyncClient, task_id: str, start_time: float):
    """Monitor task progress in a separate coroutine."""
    print("\n🔄 Starting progress monitor...\n")
    
    poll_count = 0
    seen_messages = set()
    last_state = None
    
    while poll_count < 60:  # 30 seconds max
        poll_data = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {
                "id": task_id,
                "historyLength": 50
            },
            "id": f"poll-{poll_count}"
        }
        
        try:
            response = await client.post("http://localhost:10002/", json=poll_data)
            
            if response.status_code == 200:
                result = response.json()
                
                if "result" in result:
                    task = result["result"]
                    status = task.get("status", {})
                    current_state = status.get("state")
                    
                    # Check for new messages in history
                    history = task.get("history", [])
                    for msg in history:
                        msg_id = msg.get("messageId")
                        if msg_id and msg_id not in seen_messages:
                            seen_messages.add(msg_id)
                            
                            # Only show progress messages
                            if msg.get("role") == "agent" and msg.get("metadata", {}).get("type") == "progress":
                                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                elapsed = time.time() - start_time
                                phase = msg.get("metadata", {}).get("phase", "unknown")
                                
                                parts = msg.get("parts", [])
                                for part in parts:
                                    if part.get("kind") == "text":
                                        text = part.get("text", "")
                                        print(f"[{timestamp}] (+{elapsed:.2f}s) {text}")
                    
                    # Check if state changed
                    if current_state != last_state:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        elapsed = time.time() - start_time
                        print(f"[{timestamp}] (+{elapsed:.2f}s) 📊 State: {last_state} → {current_state}")
                        last_state = current_state
                    
                    # Stop if completed
                    if current_state in ["completed", "failed", "canceled"]:
                        # Print final result
                        artifacts = task.get("artifacts", [])
                        if artifacts:
                            print(f"\n✅ Task {current_state}! Final result:")
                            for artifact in artifacts:
                                for part in artifact.get("parts", []):
                                    if part.get("kind") == "text":
                                        print(f"\n{part.get('text')}")
                        return
        
        except Exception as e:
            # Ignore errors
            pass
        
        poll_count += 1
        await asyncio.sleep(0.1)  # Poll every 100ms for faster updates

async def test_astream_progress():
    """Test progress updates with LangGraph astream."""
    url = "http://localhost:10002/"
    
    # Complex request
    send_data = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"text": "환율 정보 알려줘: 1) USD to KRW 2) EUR to KRW 3) 100달러는 몇 원?"}],
                "messageId": f"msg-{int(time.time())}",
                "contextId": "astream-test-001"
            }
        },
        "id": 1
    }
    
    print("🚀 Testing LangGraph astream progress updates...")
    print(f"Request: {json.dumps(send_data, indent=2, ensure_ascii=False)}")
    print("\n" + "="*50)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        start_time = time.time()
        
        # Send request and start monitoring in parallel
        send_task = asyncio.create_task(client.post(url, json=send_data))
        
        # Wait a bit for the request to be processed
        await asyncio.sleep(0.1)
        
        # Get initial response
        response = await send_task
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        elapsed = time.time() - start_time
        
        # Extract task ID
        task_id = None
        if "result" in result and "id" in result["result"]:
            task_id = result["result"]["id"]
            print(f"\n📋 Task created: {task_id} (in {elapsed:.2f}s)")
            
            # Check if already completed
            status = result["result"].get("status", {}).get("state")
            if status != "completed":
                # Start monitoring progress
                await monitor_task_progress(client, task_id, start_time)
            else:
                print("\n✅ Task completed immediately!")
                # Show all progress messages from history
                history = result["result"].get("history", [])
                print("\n📜 Progress history:")
                for msg in history:
                    if msg.get("role") == "agent" and msg.get("metadata", {}).get("type") == "progress":
                        parts = msg.get("parts", [])
                        for part in parts:
                            if part.get("kind") == "text":
                                print(f"  - {part.get('text')}")
                
                # Show final result
                artifacts = result["result"].get("artifacts", [])
                if artifacts:
                    print("\n📄 Final result:")
                    for artifact in artifacts:
                        for part in artifact.get("parts", []):
                            if part.get("kind") == "text":
                                print(f"\n{part.get('text')}")
        else:
            print("❌ No task ID found")

if __name__ == "__main__":
    print("Testing LangGraph astream for real-time progress updates...\n")
    asyncio.run(test_astream_progress())