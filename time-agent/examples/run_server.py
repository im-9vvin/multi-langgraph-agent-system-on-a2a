#!/usr/bin/env python
"""Example script to run the time agent server."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.time_agent.main import main

if __name__ == "__main__":
    # Run with default settings
    main.main(standalone_mode=False)