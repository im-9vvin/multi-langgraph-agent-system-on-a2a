#!/usr/bin/env python3
"""Test if astream_events is available in LangGraph."""

import asyncio
import sys
sys.path.append("src")

from orchestrator_agent.core.agent import create_orchestrator_agent
from langchain_core.messages import HumanMessage

async def test_astream_events():
    # Create orchestrator
    orchestrator = create_orchestrator_agent()
    
    # Check available methods
    print("Available streaming methods:")
    print(f"- astream: {hasattr(orchestrator, 'astream')}")
    print(f"- astream_events: {hasattr(orchestrator, 'astream_events')}")
    print(f"- ainvoke: {hasattr(orchestrator, 'ainvoke')}")
    
    # Test if astream_events works
    if hasattr(orchestrator, 'astream_events'):
        print("\nTesting astream_events...")
        initial_state = {
            "messages": [HumanMessage(content="환율 알려줘")],
            "phase": "planning"
        }
        config = {"configurable": {"thread_id": "test"}}
        
        try:
            event_count = 0
            async for event in orchestrator.astream_events(initial_state, config, version="v1"):
                event_count += 1
                print(f"Event {event_count}: {event.get('event')} - {event.get('name')}")
                if event_count > 5:  # Limit output
                    print("... (truncated)")
                    break
        except Exception as e:
            print(f"Error with astream_events: {type(e).__name__}: {e}")
    else:
        print("\nastream_events is NOT available!")
        print("This is why the fallback code is being used.")

if __name__ == "__main__":
    asyncio.run(test_astream_events())