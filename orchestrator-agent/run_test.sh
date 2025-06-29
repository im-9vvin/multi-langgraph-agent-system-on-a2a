#!/bin/bash
echo "Testing orchestrator with simple greeting..."
cd /home/march/workbench/im-9vvin/multi-langgraph-agent-system-on-a2a/orchestrator-agent
python test_simple.py "안녕하세요"

echo -e "\n\nTesting with time query..."
python test_simple.py "지금 몇시야?"

echo -e "\n\nTesting with currency query..."
python test_simple.py "원달러 환율 알려줘"