#!/usr/bin/env python3
"""Test complex request with multiple agents for astream progress."""

import asyncio
import json
import httpx
from datetime import datetime
import time

async def test_complex_astream():
    """Test with a request that requires multiple agent calls."""
    url = "http://localhost:10002/"
    
    # Very complex request requiring multiple agents and steps
    send_data = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"text": "다음을 모두 알려줘: 1) 현재 서울 시간 2) 뉴욕 시간 3) USD/KRW 환율 4) EUR/KRW 환율 5) JPY/KRW 환율 6) 100달러, 100유로, 10000엔을 각각 원화로 환전하면? 7) 총합은 얼마?"}],
                "messageId": f"msg-{int(time.time())}",
                "contextId": "complex-test-001"
            }
        },
        "id": 1
    }
    
    print("🚀 Sending complex multi-agent request...")
    print(f"Request: {json.dumps(send_data, indent=2, ensure_ascii=False)}")
    print("\n" + "="*50 + "\n")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        start_time = time.time()
        
        # Send request
        print("📤 Sending request...\n")
        response = await client.post(url, json=send_data)
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        elapsed = time.time() - start_time
        
        print(f"📥 Response received in {elapsed:.2f}s")
        
        # Check task status
        if "result" in result:
            task = result["result"]
            task_id = task.get("id")
            status = task.get("status", {}).get("state")
            
            print(f"\n📋 Task ID: {task_id}")
            print(f"📊 Status: {status}")
            
            # Show progress history
            history = task.get("history", [])
            progress_messages = []
            
            print("\n📜 Execution Timeline:")
            print("-" * 50)
            
            for msg in history:
                if msg.get("role") == "agent" and msg.get("metadata", {}).get("type") == "progress":
                    phase = msg.get("metadata", {}).get("phase", "")
                    node = msg.get("metadata", {}).get("node", "")
                    
                    parts = msg.get("parts", [])
                    for part in parts:
                        if part.get("kind") == "text":
                            text = part.get("text", "")
                            progress_messages.append({
                                "phase": phase,
                                "node": node,
                                "text": text
                            })
                            print(f"  [{phase:20}] {text}")
            
            print("-" * 50)
            
            # Show execution flow
            print("\n🔄 LangGraph Execution Flow:")
            nodes_executed = []
            for msg in progress_messages:
                if msg["node"] and msg["node"] not in nodes_executed:
                    nodes_executed.append(msg["node"])
            
            if nodes_executed:
                print("  " + " → ".join(nodes_executed))
            
            # Show final result
            artifacts = task.get("artifacts", [])
            if artifacts:
                print("\n📄 Final Result:")
                print("=" * 50)
                for artifact in artifacts:
                    for part in artifact.get("parts", []):
                        if part.get("kind") == "text":
                            print(part.get("text"))
                print("=" * 50)
            
            # Summary
            print(f"\n⏱️  Total execution time: {elapsed:.2f}s")
            print(f"📊 Progress updates received: {len(progress_messages)}")
            print(f"🔗 Nodes executed: {len(nodes_executed)}")

if __name__ == "__main__":
    print("Testing complex request with LangGraph astream...\n")
    asyncio.run(test_complex_astream())