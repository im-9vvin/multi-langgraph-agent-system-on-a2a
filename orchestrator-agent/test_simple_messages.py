#!/usr/bin/env python3
"""Test simple message generation with first 3 words."""

import sys
sys.path.append("src")

from orchestrator_agent.adapters.orchestrator_executor import OrchestratorExecutor

# Test the message generation
executor = OrchestratorExecutor()

# Test cases with various queries
test_queries = [
    "USD/KRW 환율 알려줘",
    "신라 호텔 부산에 대해 알려줘",
    "현재 시간이 몇시야?",
    "날씨가 어때?",
    "파이썬 프로그래밍에 대해 설명해줘",
    "머신러닝 알고리즘 추천해줘",
    "김치찌개 레시피 알려줘",
    "주식 시장 동향은 어때?",
    "What is the weather like today in Seoul?",
    "Tell me about machine learning algorithms and their applications",
    "안녕?",
    "오늘 점심 뭐 먹을까?"
]

phases = ["initializing", "chain_start", "plan_complete", "route_complete", "execute_complete", "aggregate_complete"]

print("Testing simple message generation with first 3 words:\n")
print("=" * 80)

for query in test_queries:
    print(f"\nQuery: {query}")
    print("-" * 40)
    
    # Only show initializing phase for clarity
    message = executor._generate_context_aware_message(query, "initializing")
    print(f"→ {message}")

print("\n" + "=" * 80)