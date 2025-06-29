#!/usr/bin/env python3
"""Test SSE functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
import httpx

async def test_sse():
    """Test SSE endpoint."""
    url = "http://localhost:10002/"
    
    # Test with SSE accept header
    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    
    data = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "content": "What is the weather?"
            }
        },
        "id": "test-1"
    }
    
    async with httpx.AsyncClient() as client:
        # Send request with SSE headers
        async with client.stream("POST", url, json=data, headers=headers) as response:
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            
            # Read SSE events
            async for line in response.aiter_lines():
                if line:
                    print(f"Event: {line}")

if __name__ == "__main__":
    asyncio.run(test_sse())