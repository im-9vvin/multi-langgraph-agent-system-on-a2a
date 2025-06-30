"""Main orchestrator agent implementation using LangGraph."""

import json
from typing import Any, Literal

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..common import get_logger
from ..common.config import config
from .state import OrchestratorState, RemoteAgentCall
from .prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    PLANNING_PROMPT,
    ROUTING_PROMPT,
    AGGREGATION_PROMPT
)
from .tools import (
    query_agent_capabilities,
    send_task_to_agent,
    wait_for_task_completion,
    parse_agent_results
)

logger = get_logger(__name__)


def get_llm():
    """Get the configured LLM instance."""
    if config.openai_api_key:
        return ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.llm_model,
            temperature=0.7,
            streaming=True
        )
    elif config.google_api_key:
        return ChatGoogleGenerativeAI(
            api_key=config.google_api_key,
            model="gemini-1.5-flash",
            temperature=0.7,
            streaming=True
        )
    else:
        raise ValueError("No LLM API key configured")


async def plan_orchestration(state: OrchestratorState) -> OrchestratorState:
    """Plan how to orchestrate the user's request."""
    logger.info("Planning orchestration")
    
    # Get the latest user message
    user_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break
    
    if not user_message:
        state["error"] = "No user message found"
        state["phase"] = "complete"
        return state
    
    # Always route to agents - no direct handling
    
    # Get agent information for context
    agents_info = """
- Currency Agent: Handles currency exchange rates and conversions
- Time Agent: Handles time-related queries and general questions
- Hotel Agent: Handles hotel search, booking, and recommendations
"""
    
    # Create orchestration plan
    llm = get_llm()
    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(agents=agents_info)
    prompt = PLANNING_PROMPT.format(user_request=user_message)
    
    # Get plan from LLM
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt)
    ])
    
    state["plan"] = response.content
    state["phase"] = "routing"
    # Don't add planning messages to the conversation
    
    return state


async def route_to_agents(state: OrchestratorState) -> OrchestratorState:
    """Determine which agents should handle which tasks."""
    logger.info("Routing to agents")
    
    llm = get_llm()
    
    # Get original user request
    user_request = ""
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            user_request = msg.content
            break
    
    # Get routing decisions
    prompt = ROUTING_PROMPT.format(plan=state["plan"], user_request=user_request)
    
    response = await llm.ainvoke([
        SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ])
    
    # Parse routing decisions
    try:
        # Extract JSON from response if present
        content = response.content
        logger.info(f"Raw routing response: {content}")
        
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            content = content[json_start:json_end].strip()
        
        routing = json.loads(content) if content.startswith("{") else {"tasks": []}
        logger.info(f"Parsed routing: {routing}")
        
        # Fix agent URLs if they are just names
        for task in routing.get("tasks", []):
            if task.get("agent_url") == "Time Agent":
                task["agent_url"] = config.agent_2_url
            elif task.get("agent_url") == "Currency Agent":
                task["agent_url"] = config.agent_1_url
            elif task.get("agent_url") == "Hotel Agent":
                task["agent_url"] = config.agent_3_url
    except Exception as e:
        logger.error(f"Failed to parse routing response: {e}")
        # Get original user message
        user_msg = ""
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                user_msg = msg.content
                break
        
        # Fallback: simple routing based on keywords
        if "환율" in user_msg or "달러" in user_msg or "currency" in user_msg.lower():
            agent_url = config.agent_1_url
        elif "호텔" in user_msg or "숙박" in user_msg or "hotel" in user_msg.lower():
            agent_url = config.agent_3_url
        else:
            agent_url = config.agent_2_url
            
        routing = {
            "tasks": [{
                "agent_url": agent_url,
                "message": user_msg,
                "parallel": True
            }]
        }
        logger.info(f"Using fallback routing: {routing}")
    
    state["routing_decision"] = routing
    state["phase"] = "executing"
    
    return state


async def execute_remote_calls(state: OrchestratorState) -> OrchestratorState:
    """Execute tasks on remote agents."""
    logger.info("Executing remote calls")
    
    routing = state.get("routing_decision", {})
    logger.info(f"Routing decision: {routing}")
    tasks = routing.get("tasks", [])
    
    if not tasks:
        logger.info("No tasks to execute - likely a help/capability request")
        state["remote_calls"] = []
        state["phase"] = "aggregating"
        return state
    
    remote_calls = []
    
    # Import httpx here for direct calls
    import httpx
    import asyncio
    
    # Create async task execution function
    async def execute_single_task(task, config):
        """Execute a single task and return the result."""
        agent_url = task.get("agent_url", config.agent_1_url)
        message = task.get("message", "")
        
        try:
            # Direct A2A call without using tools
            logger.info(f"Sending task to {agent_url}: {message}")
            
            # Create A2A message
            a2a_message = {
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "messageId": f"orch-{hash(message) % 10000}",
                        "role": "user",
                        "parts": [{"text": message}],
                        "contextId": "orchestration"
                    }
                },
                "id": 1
            }
            
            # Prepare headers
            headers = {"Content-Type": "application/json"}
            
            # Add API key header if this is Agent 3
            if agent_url == config.agent_3_url and config.agent_3_api_key:
                headers["X-API-Key"] = config.agent_3_api_key
                logger.info(f"Adding API key for {agent_url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    agent_url,
                    json=a2a_message,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    task_result = result.get("result", {})
                    task_id = task_result.get("id") or task_result.get("taskId")
                    
                    if task_id:
                        logger.info(f"Got task ID {task_id}, polling for completion")
                        
                        # Poll for completion
                        for i in range(10):
                            await asyncio.sleep(1.0)
                            
                            poll_data = {
                                "jsonrpc": "2.0",
                                "method": "tasks/get",
                                "params": {"id": task_id},
                                "id": 2
                            }
                            
                            poll_response = await client.post(
                                agent_url,
                                json=poll_data,
                                headers=headers  # Use same headers with API key
                            )
                            
                            if poll_response.status_code == 200:
                                poll_result = poll_response.json()
                                task_data = poll_result.get("result", {})
                                status = task_data.get("status", {}).get("state")
                                
                                if status == "completed":
                                    # Extract result from artifacts array
                                    result_text = ""
                                    artifacts = task_data.get("artifacts", [])
                                    for artifact in artifacts:
                                        if "parts" in artifact:
                                            for part in artifact["parts"]:
                                                if isinstance(part, dict) and part.get("kind") == "text" and "text" in part:
                                                    result_text = part["text"]
                                                    break
                                            if result_text:  # Break outer loop if we found text
                                                break
                                    
                                    
                                    return RemoteAgentCall(
                                        agent_url=agent_url,
                                        task_id=task_id,
                                        status="completed",
                                        result=result_text,
                                        error=None
                                    )
                                elif status == "failed":
                                    raise Exception("Task failed")
                        else:
                            raise Exception("Task timed out")
                    else:
                        raise ValueError("No task ID returned")
                else:
                    raise Exception(f"HTTP {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to execute task on {agent_url}: {e}")
            return RemoteAgentCall(
                agent_url=agent_url,
                task_id="",
                status="failed",
                result=None,
                error=str(e)
            )
    
    # Execute all tasks in parallel
    parallel_tasks = []
    for task in tasks:
        # Check if this task should be parallel
        if task.get("parallel", False):
            parallel_tasks.append(task)
        else:
            # Execute non-parallel tasks immediately and wait
            result = await execute_single_task(task, config)
            remote_calls.append(result)
    
    # Execute parallel tasks concurrently
    if parallel_tasks:
        logger.info(f"Executing {len(parallel_tasks)} tasks in parallel")
        results = await asyncio.gather(
            *[execute_single_task(task, config) for task in parallel_tasks],
            return_exceptions=False
        )
        remote_calls.extend(results)
    
    state["remote_calls"] = remote_calls
    state["phase"] = "aggregating"
    
    return state


async def aggregate_results(state: OrchestratorState) -> OrchestratorState:
    """Aggregate results from multiple agents."""
    logger.info("Aggregating results")
    
    llm = get_llm()
    
    # Get the original user request
    user_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break
    
    # Format results
    results = {}
    for call in state.get("remote_calls", []):
        agent_name = f"Agent at {call['agent_url']}"
        if call["status"] == "completed":
            results[agent_name] = call["result"]
        else:
            results[agent_name] = f"Failed: {call['error']}"
    
    # Create aggregation prompt
    prompt = AGGREGATION_PROMPT.format(
        user_request=user_message,
        plan=state.get("plan", ""),
        results=json.dumps(results, indent=2)
    )
    
    # Get aggregated response
    response = await llm.ainvoke([
        SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ])
    
    state["aggregated_results"] = {"response": response.content}
    state["messages"].append(AIMessage(content=response.content))
    state["phase"] = "complete"
    
    return state


def should_continue(state: OrchestratorState) -> Literal["plan", "route", "execute", "aggregate", "end"]:
    """Determine the next step in orchestration."""
    phase = state.get("phase", "planning")
    
    if phase == "planning":
        return "plan"
    elif phase == "routing":
        return "route"
    elif phase == "executing":
        return "execute"
    elif phase == "aggregating":
        return "aggregate"
    else:
        return "end"


def create_orchestrator_agent():
    """Create the orchestrator agent graph."""
    # Create the graph
    workflow = StateGraph(OrchestratorState)
    
    # Add nodes
    workflow.add_node("plan", plan_orchestration)
    workflow.add_node("route", route_to_agents)
    workflow.add_node("execute", execute_remote_calls)
    workflow.add_node("aggregate", aggregate_results)
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "plan",
        should_continue,
        {
            "route": "route",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "route",
        should_continue,
        {
            "execute": "execute",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "execute",
        should_continue,
        {
            "aggregate": "aggregate",
            "end": END
        }
    )
    
    workflow.add_edge("aggregate", END)
    
    # Set entry point
    workflow.set_entry_point("plan")
    
    # Create checkpointer
    checkpointer = MemorySaver()
    
    # Compile the graph
    return workflow.compile(checkpointer=checkpointer)