#!/usr/bin/env python3
"""Test which event flow is being used."""

import asyncio
import logging
import sys
sys.path.append("src")

from orchestrator_agent.adapters.orchestrator_executor import OrchestratorExecutor
from orchestrator_agent.core.agent import create_orchestrator_agent

# Setup logging to see which path is taken
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

async def main():
    # Create orchestrator
    orchestrator = create_orchestrator_agent()
    
    # Check if astream_events is available
    has_astream_events = hasattr(orchestrator, 'astream_events')
    print(f"astream_events available: {has_astream_events}")
    
    if has_astream_events:
        print("The orchestrator should use the detailed event flow with phase-specific messages")
    else:
        print("The orchestrator will fall back to simple astream with hardcoded messages")
    
    # Test what version of langchain/langgraph is installed
    try:
        import langgraph
        print(f"LangGraph version: {langgraph.__version__ if hasattr(langgraph, '__version__') else 'unknown'}")
    except:
        pass

if __name__ == "__main__":
    asyncio.run(main())