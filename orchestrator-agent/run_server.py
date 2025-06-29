#!/usr/bin/env python3
"""Run the orchestrator server directly."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import uvicorn
from orchestrator_agent.server.app import create_app

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="localhost", port=10002)