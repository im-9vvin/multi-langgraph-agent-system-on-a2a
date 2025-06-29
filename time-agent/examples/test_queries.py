#!/usr/bin/env python
"""Example queries for testing the time agent."""

import httpx
import json
import time
import asyncio


async def send_query(query: str, client: httpx.AsyncClient):
    """Send a query to the time agent and get the response."""
    message = {
        "jsonrpc": "2.0",
        "method": "message",
        "params": {
            "messages": [
                {"role": "user", "content": query}
            ]
        },
        "id": f"test-{int(time.time())}"
    }
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    try:
        # Send message
        response = await client.post("http://localhost:10001/message", json=message)
        result = response.json()
        
        if "result" in result and "task_id" in result["result"]:
            task_id = result["result"]["task_id"]
            print(f"Task ID: {task_id}")
            
            # Poll for completion
            for i in range(15):  # 30 seconds max
                await asyncio.sleep(2)
                task_response = await client.get(f"http://localhost:10001/tasks/{task_id}")
                
                if task_response.status_code == 200:
                    task_data = task_response.json()
                    status = task_data.get("status")
                    
                    if status == "completed":
                        print(f"Status: {status}")
                        if "artifacts" in task_data:
                            for artifact in task_data["artifacts"]:
                                if artifact.get("type") == "text":
                                    print(f"\nResponse: {artifact.get('data')}")
                        break
                    elif status == "failed":
                        print(f"Task failed: {task_data.get('error')}")
                        break
                    else:
                        print(f"Status: {status}...")
        else:
            print(f"Error: {result}")
            
    except Exception as e:
        print(f"Query failed: {e}")


async def main():
    """Run example queries."""
    queries = [
        "What time is it in Tokyo?",
        "What's the current time in New York?",
        "Convert 3:30 PM EST to London time",
        "What time is 14:00 in Paris when converted to Singapore?",
        "Show me the time difference between Los Angeles and Sydney",
        "What time is it right now in UTC?",
        "Is it currently daylight saving time in New York?",
    ]
    
    print("Testing Time Agent with example queries...")
    print("Server should be running at http://localhost:10001")
    
    # Test if server is running
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            health = await client.get("http://localhost:10001/health")
            if health.status_code != 200:
                print("Server is not responding. Please start the server first.")
                return
                
            print("Server is running!")
            
            # Run queries
            for query in queries:
                await send_query(query, client)
                await asyncio.sleep(1)  # Small delay between queries
                
    except httpx.ConnectError:
        print("Cannot connect to server. Please run: uv run time-agent")


if __name__ == "__main__":
    asyncio.run(main())