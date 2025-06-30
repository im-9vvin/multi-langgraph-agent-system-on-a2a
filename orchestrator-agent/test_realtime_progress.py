#!/usr/bin/env python3
"""Test real-time progress updates with immediate response."""

import asyncio
import json
import httpx
from datetime import datetime
import time

async def test_realtime_progress():
    """Test progress updates with immediate response and background polling."""
    url = "http://localhost:10002/"
    
    # Complex request that requires multiple steps
    send_data = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"text": "1. USD to KRW 환율 알려줘 2. EUR to KRW 환율도 알려줘 3. 100달러와 100유로를 각각 원화로 환전하면 얼마야?"}],
                "messageId": f"msg-{int(time.time())}",
                "contextId": "realtime-test-001"
            }
        },
        "id": 1
    }
    
    print("🚀 Sending complex multi-step request...")
    print(f"Request: {json.dumps(send_data, indent=2, ensure_ascii=False)}")
    print("\n" + "="*50 + "\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Send message (expecting immediate response with task ID)
        start_time = time.time()
        
        # Create two tasks: one for sending, one for polling
        async def send_request():
            response = await client.post(url, json=send_data)
            return response
        
        async def poll_progress(task_id):
            """Poll for progress updates."""
            poll_count = 0
            last_status = None
            last_message = None
            progress_updates = []
            
            while poll_count < 40:  # 20 seconds max
                poll_data = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {
                        "id": task_id,
                        "historyLength": 20
                    },
                    "id": poll_count + 100
                }
                
                try:
                    poll_response = await client.post(url, json=poll_data)
                    
                    if poll_response.status_code == 200:
                        poll_result = poll_response.json()
                        
                        if "result" in poll_result:
                            task = poll_result["result"]
                            status = task.get("status", {})
                            current_status = status.get("state")
                            
                            # Check history for new progress messages
                            history = task.get("history", [])
                            for msg in history:
                                if msg.get("role") == "agent" and msg.get("metadata", {}).get("type") == "progress":
                                    msg_id = msg.get("messageId")
                                    if msg_id not in progress_updates:
                                        progress_updates.append(msg_id)
                                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                        elapsed = time.time() - start_time
                                        parts = msg.get("parts", [])
                                        for part in parts:
                                            if part.get("kind") == "text":
                                                text = part.get("text", "")
                                                phase = msg.get("metadata", {}).get("phase", "")
                                                print(f"[{timestamp}] (+{elapsed:.2f}s) 📊 [{phase}] {text}")
                            
                            # Check if task is completed
                            if current_status in ["completed", "failed", "canceled"]:
                                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                elapsed = time.time() - start_time
                                print(f"\n[{timestamp}] (+{elapsed:.2f}s) ✅ Task {current_status}!")
                                
                                # Print final result
                                artifacts = task.get("artifacts", [])
                                if artifacts:
                                    print("\n📄 Final Result:")
                                    for artifact in artifacts:
                                        for part in artifact.get("parts", []):
                                            if part.get("kind") == "text":
                                                print(f"\n{part.get('text')}")
                                
                                return current_status
                            
                            last_status = current_status
                except Exception as e:
                    # Ignore polling errors
                    pass
                
                poll_count += 1
                await asyncio.sleep(0.25)  # Poll every 250ms
            
            return "timeout"
        
        # Send request
        print("📤 Sending request...\n")
        response = await send_request()
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        response_time = time.time() - start_time
        print(f"📥 Initial response received in {response_time:.2f}s")
        
        # Extract task ID
        task_id = None
        if "result" in result and "id" in result["result"]:
            task_id = result["result"]["id"]
            initial_status = result["result"].get("status", {}).get("state", "unknown")
            print(f"📋 Task ID: {task_id}")
            print(f"📊 Initial Status: {initial_status}")
            
            # Check if already completed
            if initial_status == "completed":
                print("\n✅ Task already completed in initial response!")
                artifacts = result["result"].get("artifacts", [])
                if artifacts:
                    print("\n📄 Result:")
                    for artifact in artifacts:
                        for part in artifact.get("parts", []):
                            if part.get("kind") == "text":
                                print(f"\n{part.get('text')}")
            else:
                # Start polling for updates
                print("\n🔄 Monitoring progress...\n")
                final_status = await poll_progress(task_id)
                
                if final_status == "timeout":
                    print("\n⏱️ Polling timed out")
        else:
            print("❌ No task ID found in response")

if __name__ == "__main__":
    print("Testing real-time progress updates...\n")
    asyncio.run(test_realtime_progress())