#!/usr/bin/env python3
"""Test SSE streaming with complex request."""

import asyncio
import json
import httpx
import time
from datetime import datetime

async def test_complex_sse():
    """Test SSE with a complex multi-agent request."""
    url = "http://localhost:10002/"
    
    # Complex request
    data = {
        "jsonrpc": "2.0",
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "parts": [{
                    "text": "다음을 알려줘: 1) USD/KRW 환율 2) EUR/KRW 환율 3) 100달러와 100유로를 원화로 환전하면?"
                }],
                "messageId": f"msg-{int(time.time())}",
                "contextId": "complex-stream-001"
            }
        },
        "id": "complex-1"
    }
    
    print("🚀 Testing SSE streaming with complex request...")
    print(f"Request: {json.dumps(data, indent=2, ensure_ascii=False)}")
    print("\n" + "="*50 + "\n")
    
    start_time = time.time()
    events_received = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST", 
            url,
            json=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
        ) as response:
            print(f"Response Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print("\n📊 Real-time Progress:\n")
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        event_data = line[6:]
                        if event_data.strip():
                            elapsed = time.time() - start_time
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            
                            event = json.loads(event_data)
                            events_received.append(event)
                            
                            if "result" in event:
                                result = event["result"]
                                
                                # Task creation
                                if result.get("kind") == "task":
                                    print(f"[{timestamp}] (+{elapsed:.2f}s) ✅ Task created: {result.get('id')}")
                                
                                # Status updates
                                elif result.get("kind") == "status-update":
                                    status = result.get("status", {})
                                    state = status.get("state")
                                    message = status.get("message")
                                    
                                    if isinstance(message, dict) and message.get("parts"):
                                        # Extract text from message parts
                                        text = message["parts"][0].get("text", "") if message["parts"] else ""
                                        print(f"[{timestamp}] (+{elapsed:.2f}s) 📌 [{state}] {text}")
                                    else:
                                        print(f"[{timestamp}] (+{elapsed:.2f}s) 📌 Status: {state}")
                                    
                                    if result.get("final"):
                                        print(f"[{timestamp}] (+{elapsed:.2f}s) ✅ Stream completed!")
                                
                                # Artifact updates
                                elif result.get("kind") == "artifact-update":
                                    artifact = result.get("artifact", {})
                                    name = artifact.get("name", "unnamed")
                                    print(f"[{timestamp}] (+{elapsed:.2f}s) 📄 Artifact: {name}")
                                    
                                    # Show preview of content
                                    for part in artifact.get("parts", []):
                                        if part.get("kind") == "text":
                                            text = part.get("text", "")
                                            preview = text[:80] + "..." if len(text) > 80 else text
                                            print(f"            Preview: {preview}")
                                
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                    except Exception as e:
                        print(f"Error processing event: {e}")
    
    # Summary
    total_time = time.time() - start_time
    print(f"\n📊 Summary:")
    print(f"  - Total time: {total_time:.2f}s")
    print(f"  - Events received: {len(events_received)}")
    
    # Count event types
    event_types = {}
    for event in events_received:
        if "result" in event:
            kind = event["result"].get("kind", "unknown")
            event_types[kind] = event_types.get(kind, 0) + 1
    
    print(f"  - Event types: {event_types}")

if __name__ == "__main__":
    print("Testing SSE streaming with complex orchestration...\n")
    asyncio.run(test_complex_sse())