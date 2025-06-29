#!/usr/bin/env python3
"""Run the orchestrator with A2A SDK."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Now run the server
from orchestrator_agent.main import main

if __name__ == "__main__":
    # Run with default options
    main.callback(host="localhost", port=10002, log_level="INFO")