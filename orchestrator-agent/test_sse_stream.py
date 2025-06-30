#!/usr/bin/env python3
"""Test SSE streaming with message/stream endpoint."""

import asyncio
import json
import httpx
import time
from typing import AsyncIterator

async def test_sse_stream():
    """Test the message/stream endpoint with SSE."""
    url = "http://localhost:10002/"
    
    # Create request with message/stream method
    data = {
        "jsonrpc": "2.0",
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"text": "현재 환율은 얼마야? USD to KRW"}],
                "messageId": f"msg-{int(time.time())}",
                "contextId": "test-stream-001"
            }
        },
        "id": "stream-test-1"
    }
    
    print("Sending streaming request...")
    print(f"Request: {json.dumps(data, indent=2, ensure_ascii=False)}")
    print("\n" + "="*50 + "\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
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
            print(f"Response Headers: {dict(response.headers)}")
            print("\nSSE Events:\n")
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        # Parse SSE data
                        event_data = line[6:]  # Remove "data: " prefix
                        if event_data.strip():
                            event = json.loads(event_data)
                            
                            # Extract result from JSON-RPC response
                            if "result" in event:
                                result = event["result"]
                                
                                # Check event type
                                if result.get("kind") == "task":
                                    print(f"📋 Task Created: {result.get('id')}")
                                    print(f"   Status: {result.get('status', {}).get('state')}")
                                    
                                elif result.get("kind") == "status-update":
                                    status = result.get("status", {})
                                    print(f"📊 Status Update: {status.get('state')}")
                                    if status.get("message"):
                                        print(f"   Message: {status.get('message')}")
                                    if result.get("final"):
                                        print("   ✅ Final update received")
                                        
                                elif result.get("kind") == "artifact-update":
                                    artifact = result.get("artifact", {})
                                    print(f"📄 Artifact Update: {artifact.get('name', 'unnamed')}")
                                    for part in artifact.get("parts", []):
                                        if part.get("kind") == "text":
                                            print(f"   Content: {part.get('text')[:100]}...")
                                            
                                print()
                    except json.JSONDecodeError as e:
                        print(f"Error parsing SSE data: {e}")
                        print(f"Raw data: {line}")
                elif line.strip():
                    # Other SSE fields (event, id, retry, etc.)
                    print(f"SSE Field: {line}")

if __name__ == "__main__":
    print("Testing A2A message/stream endpoint with SSE...\n")
    asyncio.run(test_sse_stream())