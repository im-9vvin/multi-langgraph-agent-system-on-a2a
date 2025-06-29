#!/usr/bin/env python
"""Simple test for time agent."""

import httpx
import json


def test_time_query():
    """Test a simple time query."""
    url = "http://localhost:10001/message"
    
    message = {
        "jsonrpc": "2.0",
        "method": "message",
        "params": {
            "messages": [
                {"role": "user", "content": "What time is it in Tokyo?"}
            ]
        },
        "id": "test-tokyo-1"
    }
    
    print("Sending query: What time is it in Tokyo?")
    
    try:
        response = httpx.post(url, json=message, timeout=30.0)
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_time_query()