#!/usr/bin/env python
"""Test A2A message endpoint directly."""

import httpx
import json


def test_a2a_message():
    """Test the A2A message endpoint."""
    url = "http://localhost:10001/message"
    
    message = {
        "jsonrpc": "2.0",
        "method": "message",
        "params": {
            "messages": [
                {"role": "user", "content": "What time is it in Tokyo?"}
            ]
        },
        "id": "test-1"
    }
    
    try:
        response = httpx.post(url, json=message, timeout=30.0)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_a2a_message()