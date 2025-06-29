#!/bin/bash

echo "Starting status update test..."
echo "=============================="

# Ensure agents are running
echo "Checking if agents are running..."
curl -s http://localhost:10000/health > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⚠️  Currency Agent (10000) is not running"
fi

curl -s http://localhost:10001/health > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⚠️  Time Agent (10001) is not running"
fi

curl -s http://localhost:10002/health > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⚠️  Orchestrator Agent (10002) is not running"
fi

echo ""
echo "Running test..."
python test_status_updates.py