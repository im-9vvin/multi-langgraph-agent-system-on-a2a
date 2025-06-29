#!/usr/bin/env -S uv run python
"""
Example: Running the Currency Agent as a server.

This example shows how to start the Currency Agent server
with custom configuration.

Run with: uv run python examples/run_server.py
"""

import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.currency_agent.main import main


if __name__ == '__main__':
    # You can also set environment variables here
    # os.environ['TOOL_MODEL_NAME'] = 'gpt-4'
    
    # Run the server
    main(['--host', 'localhost', '--port', '10000', '--log-level', 'INFO'])