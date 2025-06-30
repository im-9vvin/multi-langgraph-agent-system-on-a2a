#!/usr/bin/env python3
"""Test agent-specific message generation."""

import sys
sys.path.append("src")

from orchestrator_agent.adapters.orchestrator_executor import OrchestratorExecutor

# Test the message generation
executor = OrchestratorExecutor()

print("Testing agent-specific message generation:\n")
print("=" * 80)

# Test single agent scenario
query = "현재 환율 알려줘"
print(f"\n1. Single Agent Query: {query}")
print("-" * 40)
print("초기화:", executor._generate_context_aware_message(query, "initializing"))
print("계획수립:", executor._generate_context_aware_message(query, "plan_complete", {"agent_count": 1}))
print("라우팅:", executor._generate_context_aware_message(query, "route_complete", {"agents": ["환율 서비스"]}))
print("실행완료:", executor._generate_context_aware_message(query, "execute_complete", {"agent_name": "환율 서비스"}))
print("종합:", executor._generate_context_aware_message(query, "aggregate_complete", {"result_count": 1}))

# Test multiple agents scenario
query = "USD/KRW 환율이랑 지금 뉴욕 시간 알려줘"
print(f"\n2. Multiple Agents Query: {query}")
print("-" * 40)
print("초기화:", executor._generate_context_aware_message(query, "initializing"))
print("계획수립:", executor._generate_context_aware_message(query, "plan_complete", {"agent_count": 2}))
print("라우팅:", executor._generate_context_aware_message(query, "route_complete", {"agents": ["환율 서비스", "시간 서비스"]}))
print("실행1:", executor._generate_context_aware_message(query, "execute_complete", {"agent_name": "환율 서비스"}))
print("실행2:", executor._generate_context_aware_message(query, "execute_complete", {"agent_name": "시간 서비스"}))
print("종합:", executor._generate_context_aware_message(query, "aggregate_complete", {"result_count": 2}))

# Test three agents scenario
query = "서울 호텔 추천하고 환율이랑 현재 시간도 알려줘"
print(f"\n3. Three Agents Query: {query}")
print("-" * 40)
print("초기화:", executor._generate_context_aware_message(query, "initializing"))
print("계획수립:", executor._generate_context_aware_message(query, "plan_complete", {"agent_count": 3}))
print("라우팅:", executor._generate_context_aware_message(query, "route_complete", {"agents": ["호텔 서비스", "환율 서비스", "시간 서비스"]}))
print("실행1:", executor._generate_context_aware_message(query, "execute_complete", {"agent_name": "호텔 서비스"}))
print("실행2:", executor._generate_context_aware_message(query, "execute_complete", {"agent_name": "환율 서비스"}))
print("실행3:", executor._generate_context_aware_message(query, "execute_complete", {"agent_name": "시간 서비스"}))
print("종합:", executor._generate_context_aware_message(query, "aggregate_complete", {"result_count": 3}))

print("\n" + "=" * 80)