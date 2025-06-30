#!/usr/bin/env python3
"""Test dynamic message generation for various topics."""

import sys
sys.path.append("src")

from orchestrator_agent.adapters.orchestrator_executor import OrchestratorExecutor

# Test the message generation
executor = OrchestratorExecutor()

# Test cases with various topics
test_queries = [
    "USD/KRW 환율 알려줘",
    "신라 호텔 부산에 대해 알려줘",
    "현재 시간이 몇시야?",
    "날씨가 어때?",
    "파이썬 프로그래밍에 대해 설명해줘",
    "머신러닝 알고리즘 추천해줘",
    "김치찌개 레시피 알려줘",
    "주식 시장 동향은 어때?",
    "What is the weather like?",
    "Tell me about machine learning"
]

phases = [
    "initializing",
    "chain_start", 
    "plan_complete",
    "route_complete",
    "execute_complete",
    "aggregate_complete"
]

print("Testing dynamic message generation:\n")
print("=" * 80)

for query in test_queries:
    print(f"\nQuery: {query}")
    print("-" * 40)
    
    for phase in phases:
        message = executor._generate_context_aware_message(query, phase)
        print(f"{phase:20} | {message}")
    
    print()

print("=" * 80)