#!/usr/bin/env python3
"""Test imports."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    print("Testing imports...")
    
    print("1. Config...")
    from orchestrator_agent.common.config import config
    print(f"   - API key exists: {bool(config.openai_api_key)}")
    
    print("2. Core agent...")
    from orchestrator_agent.core.agent import create_orchestrator_agent
    print("   - OK")
    
    print("3. Orchestrator executor...")
    from orchestrator_agent.adapters.orchestrator_executor import OrchestratorExecutor
    print("   - OK")
    
    print("4. A2A app...")
    from orchestrator_agent.server.a2a_app import create_app
    print("   - OK")
    
    print("\nAll imports successful!")
    
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()