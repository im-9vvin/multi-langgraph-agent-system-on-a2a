#!/usr/bin/env python3
"""Check if agents are running."""

import httpx
import asyncio

async def check_agent(url, name):
    """Check if an agent is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/health")
            if response.status_code == 200:
                print(f"✅ {name} is running at {url}")
                return True
            else:
                print(f"❌ {name} returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ {name} is not running at {url}: {e}")
        return False

async def main():
    """Check all agents."""
    print("Checking agents...")
    print("-" * 50)
    
    agents = [
        ("http://localhost:10000", "Currency Agent"),
        ("http://localhost:10001", "Time Agent"),
        ("http://localhost:10002", "Orchestrator Agent")
    ]
    
    results = []
    for url, name in agents:
        result = await check_agent(url, name)
        results.append(result)
    
    print("-" * 50)
    if all(results):
        print("✅ All agents are running!")
    else:
        print("⚠️  Some agents are not running")
        print("\nTo start agents:")
        print("1. Currency Agent: cd currency-agent-v0.4.0 && uv run python -m currency_agent.server")
        print("2. Time Agent: cd time-agent && uv run python -m time_agent.server")
        print("3. Orchestrator Agent: cd orchestrator-agent && uv run python run_server.py")

if __name__ == "__main__":
    asyncio.run(main())