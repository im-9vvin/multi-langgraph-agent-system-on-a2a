#!/bin/bash
cd /home/march/workbench/im-9vvin/multi-langgraph-agent-system-on-a2a/orchestrator-agent
export OPENAI_API_KEY="your-key-here"
export A2A_HOST=localhost
export A2A_PORT=10002
export AGENT_1_URL=http://localhost:10000
export AGENT_2_URL=http://localhost:10001

echo "Starting Orchestrator Agent on port 10002..."
uv run python run_server.py