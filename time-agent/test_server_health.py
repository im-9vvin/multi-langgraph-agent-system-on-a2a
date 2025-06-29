#!/usr/bin/env python
"""Test server health endpoint."""

import httpx
import asyncio


async def test_health():
    """Test the health endpoint."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8002/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error: {e}")
            print("Make sure the server is running!")


if __name__ == "__main__":
    asyncio.run(test_health())