"""A2A Protocol executor for orchestrator agent."""

import logging
import asyncio
import json
from typing import Optional, Dict, Any

import httpx

# A2A protocol imports
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Part,
    TaskState,
    TextPart,
    InvalidParamsError,
)
from a2a.utils import new_task
from a2a.utils.errors import ServerError

# Internal imports
from ..common import get_logger
from ..common.config import config
from ..core.agent import create_orchestrator_agent
from ..core.state import OrchestratorState
from langchain_core.messages import HumanMessage
from .agent_discovery import agent_registry

logger = get_logger(__name__)


class OrchestratorExecutor(AgentExecutor):
    """
    A2A Protocol executor for Orchestrator Agent.
    
    This executor handles A2A requests and orchestrates multiple remote agents.
    """
    
    def __init__(self):
        """Initialize executor."""
        # Create httpx client for calling other agents
        self.httpx_client = httpx.AsyncClient(timeout=10.0)
        # Create LangGraph orchestrator
        self.orchestrator = create_orchestrator_agent()
        # Flag to track if agents have been discovered
        self._agents_discovered = False
        
    async def _ensure_agents_discovered(self):
        """Ensure agents are discovered before first use."""
        if not self._agents_discovered:
            default_agents = config.get_remote_agents()
            logger.info(f"Discovering agents: {default_agents}")
            await agent_registry.discover_multiple(default_agents)
            self._agents_discovered = True
        
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute an A2A request.
        
        Args:
            context: Request context containing user input and task info
            event_queue: A2A event queue for sending events to client
        """
        # Get user input
        query = context.get_user_input()
        if not query:
            raise ServerError(error=InvalidParamsError(message="No user input provided"))
        
        # Get or create A2A SDK task
        sdk_task = context.current_task
        if not sdk_task:
            sdk_task = new_task(context.message)
            await event_queue.enqueue_event(sdk_task)
        
        # Create task updater for A2A SDK
        updater = TaskUpdater(event_queue, sdk_task.id, sdk_task.contextId)
        
        try:
            # Ensure agents are discovered
            await self._ensure_agents_discovered()
            
            # Update task status to working
            await updater.update_status(TaskState.working)
            
            # Handle request directly, not in background
            await self._handle_request(query, sdk_task.contextId, updater)
            
        except Exception as e:
            logger.error("Orchestration failed", error=str(e))
            await updater.add_artifact(
                [Part(root=TextPart(text=f"죄송합니다. 오류가 발생했습니다: {str(e)}"))],
                name="error.txt"
            )
            await updater.update_status(TaskState.failed)
    
    async def _handle_request(self, query: str, context_id: str, updater: TaskUpdater) -> None:
        """
        Handle all requests asynchronously.
        
        Args:
            query: User query
            context_id: Context ID
            updater: Task updater
        """
        try:
            # Handle simple greetings and meta questions directly
            simple_greetings = ["안녕", "hello", "hi", "hey", "안녕하세요", "하이", "반가워"]
            meta_questions = ["뭘 해줄", "뭘 할 수", "무엇을 할 수", "what can you do", "기능", "도움"]
            
            if any(greeting in query.lower() for greeting in simple_greetings):
                response = "안녕하세요! 무엇을 도와드릴까요?"
            elif any(question in query.lower() for question in meta_questions):
                response = """저는 여러 AI 에이전트를 조율하는 오케스트레이터입니다. 
                
다음과 같은 일을 도와드릴 수 있습니다:
- 환율 조회 및 환전 계산 (USD, EUR, JPY 등)
- 일반적인 질문에 대한 답변
- 여러 작업을 동시에 처리

예시:
- "USD 100달러는 원화로 얼마야?"
- "유로 환율 알려줘"
- "지금 뉴욕은 몇시야?"

무엇을 도와드릴까요?"""
            else:
                # Use LangGraph orchestrator for LLM-based routing
                response = await self._orchestrate_with_langgraph(query, context_id)
            
            # Send final response
            await updater.add_artifact(
                [Part(root=TextPart(text=response))],
                name="response.txt"
            )
            
            # Complete the task
            await updater.complete()
            
        except Exception as e:
            logger.error(f"Request handling failed: {e}")
            await updater.add_artifact(
                [Part(root=TextPart(text=f"죄송합니다. 오류가 발생했습니다: {str(e)}"))],
                name="error.txt"
            )
            await updater.update_status(TaskState.failed)
    
    async def _orchestrate_with_langgraph(self, query: str, context_id: str) -> str:
        """
        Orchestrate using LangGraph with LLM-based routing.
        
        Args:
            query: User query
            context_id: Context ID
            
        Returns:
            Final orchestrated response
        """
        try:
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=query)],
                "phase": "planning",
                "plan": None,
                "routing_decision": None,
                "remote_calls": [],
                "aggregated_results": None,
                "error": None
            }
            
            
            # Run orchestrator
            logger.info(f"Running LangGraph orchestrator for query: {query}")
            config = {"configurable": {"thread_id": context_id}}
            
            # Run the orchestrator to completion
            final_state = await self.orchestrator.ainvoke(initial_state, config)
            
            logger.info(f"Final orchestrator state phase: {final_state.get('phase')}")
            
            # Extract final response from messages
            if final_state and "messages" in final_state:
                for msg in reversed(final_state["messages"]):
                    if hasattr(msg, "content") and hasattr(msg, "type"):
                        if msg.type == "ai":  # AIMessage from aggregation
                            logger.info(f"Found AI response: {msg.content}")
                            return msg.content
            
            # Check aggregated results
            if final_state and "aggregated_results" in final_state and final_state["aggregated_results"]:
                response = final_state["aggregated_results"].get("response", "")
                if response:
                    logger.info(f"Found aggregated response: {response}")
                    return response
            
            # Check remote calls for direct results
            if final_state and "remote_calls" in final_state:
                results = []
                for call in final_state["remote_calls"]:
                    if call.get("status") == "completed" and call.get("result"):
                        results.append(call["result"])
                if results:
                    return "\n".join(results)
            
            logger.error(f"No response found in final state: {final_state}")
            return "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다."
            
        except Exception as e:
            logger.error(f"LangGraph orchestration failed: {e}", exc_info=True)
            
            # Fallback to direct A2A routing
            logger.info("Falling back to direct A2A routing")
            
            # Simple keyword-based routing
            query_lower = query.lower()
            
            if "환율" in query_lower or "달러" in query_lower or "exchange" in query_lower or "원" in query_lower:
                # Try currency agent
                response = await self._call_agent("http://localhost:10000", query, context_id)
                if response:
                    return response
            
            elif "시간" in query_lower or "몇시" in query_lower or "time" in query_lower:
                # Try time agent
                response = await self._call_agent("http://localhost:10001", query, context_id)
                if response:
                    return response
            
            elif "도와" in query_lower or "help" in query_lower or "뭘" in query_lower:
                # Explain capabilities
                return """저는 다음과 같은 도움을 드릴 수 있습니다:
                
1. 환율 정보: 원달러, 유로, 엔화 등의 실시간 환율 조회
2. 시간 정보: 현재 시간 및 세계 시간 조회
3. 일반 질문: 다양한 주제에 대한 답변

예시:
- "원달러 환율 알려줘"
- "지금 몇시야?"
- "유로 환율은?"

무엇을 도와드릴까요?"""
            
            # Default: try general agent
            response = await self._call_agent("http://localhost:10001", query, context_id)
            if response:
                return response
                    
            return "죄송합니다. 요청을 처리할 수 없습니다."
    
    async def _handle_orchestration(self, query: str, context_id: str, updater: TaskUpdater) -> None:
        """
        Handle orchestration asynchronously.
        
        Args:
            query: User query
            context_id: Context ID
            updater: Task updater
        """
        try:
            # Orchestrate the request
            response = await self._orchestrate_request(query, context_id)
            
            # Send final response
            await updater.add_artifact(
                [Part(root=TextPart(text=response))],
                name="response.txt"
            )
            
            # Complete the task
            await updater.complete()
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            await updater.add_artifact(
                [Part(root=TextPart(text=f"죄송합니다. 오류가 발생했습니다: {str(e)}"))],
                name="error.txt"
            )
            await updater.update_status(TaskState.failed)
    
    async def _orchestrate_request(self, query: str, context_id: str) -> str:
        """
        Orchestrate the request by calling appropriate agents.
        
        Args:
            query: User query
            context_id: Context ID for the conversation
            
        Returns:
            Final orchestrated response
        """
        # Check what the query is about
        query_lower = query.lower()
        
        # Currency-related keywords
        currency_keywords = ["환율", "환전", "exchange", "currency", "usd", "eur", "jpy", "krw", "달러", "유로", "엔", "원"]
        
        # Time-related keywords  
        time_keywords = ["시간", "몇시", "time", "what time", "현재", "지금", "몇 시"]
        
        responses = {}
        
        # Route to appropriate agents
        if any(keyword in query_lower for keyword in currency_keywords):
            # Call currency agent
            response = await self._call_agent("http://localhost:10000", query, context_id)
            if response:
                responses["currency"] = response
        
        elif any(keyword in query_lower for keyword in time_keywords):
            # Call general agent for time queries
            response = await self._call_agent("http://localhost:10001", query, context_id)
            if response:
                responses["time"] = response
        
        else:
            # For other queries, use general agent
            response = await self._call_agent("http://localhost:10001", query, context_id)
            if response:
                responses["general"] = response
        
        # Combine responses
        if responses:
            # If we have responses, return them
            return "\n".join(responses.values())
        else:
            # Fallback response based on query type
            if any(keyword in query_lower for keyword in currency_keywords):
                return "죄송합니다. 현재 환율 정보를 가져올 수 없습니다. 잠시 후 다시 시도해주세요."
            elif any(keyword in query_lower for keyword in time_keywords):
                return "죄송합니다. 현재 시간 정보를 가져올 수 없습니다. 잠시 후 다시 시도해주세요."
            else:
                return f"'{query}'에 대한 답변을 찾을 수 없습니다. 다른 질문을 해주세요."
    
    async def _call_agent(self, agent_url: str, query: str, context_id: str) -> Optional[str]:
        """
        Call a remote A2A agent and get response.
        
        Args:
            agent_url: URL of the agent
            query: User query
            context_id: Context ID
            
        Returns:
            Agent response or None if failed
        """
        try:
            # Create A2A message
            message = {
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "messageId": f"orch-{context_id}-{asyncio.get_event_loop().time()}",
                        "role": "user",
                        "parts": [
                            {"text": query}
                        ],
                        "contextId": context_id
                    }
                },
                "id": 1
            }
            
            
            # Send request
            response = await self.httpx_client.post(
                agent_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Initial response from {agent_url}: {json.dumps(result, indent=2)}")
                
                # Get task ID
                if "result" in result:
                    task_result = result["result"]
                    # Try different possible fields for task ID
                    task_id = task_result.get("id") or task_result.get("taskId") or task_result.get("task", {}).get("id")
                    
                    if task_id:
                        logger.info(f"Got task ID: {task_id}, starting to poll...")
                        
                        
                        # Poll for completion
                        return await self._poll_task(agent_url, task_id)
                    else:
                        logger.error(f"No task ID found in response: {result}")
                        return None
            
            logger.error(f"Agent call failed: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error calling agent {agent_url}: {e}")
            return None
    
    async def _poll_task(self, agent_url: str, task_id: str, max_attempts: int = 10) -> Optional[str]:
        """
        Poll a task until completion using JSON-RPC.
        
        Args:
            agent_url: URL of the agent
            task_id: Task ID to poll
            max_attempts: Maximum polling attempts
            
        Returns:
            Final response or None
        """
        for attempt in range(max_attempts):
            try:
                # Create JSON-RPC request for task status
                poll_data = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {"id": task_id},
                    "id": attempt + 2  # Different ID from initial request
                }
                
                # Send poll request
                response = await self.httpx_client.post(
                    agent_url,
                    json=poll_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if "result" in result:
                        task = result["result"]
                        status = task.get("status", {}).get("state")
                        
                        if status == "completed":
                            logger.info(f"Task {task_id} completed! Full task data: {json.dumps(task, indent=2)}")
                            
                            # Check for artifacts array (plural)
                            if "artifacts" in task and task["artifacts"]:
                                for artifact in task["artifacts"]:
                                    if "parts" in artifact:
                                        for part in artifact["parts"]:
                                            if isinstance(part, dict) and "text" in part:
                                                logger.info(f"Found response text: {part['text']}")
                                                return part["text"]
                            
                            # Check for single artifact
                            if "artifact" in task and task["artifact"]:
                                artifact = task["artifact"]
                                if "parts" in artifact:
                                    for part in artifact["parts"]:
                                        if isinstance(part, dict) and "text" in part:
                                            logger.info(f"Found response text: {part['text']}")
                                            return part["text"]
                            
                            # Fallback to messages if no artifact
                            messages = task.get("messages", [])
                            for msg in messages:
                                if msg.get("role") == "assistant":
                                    parts = msg.get("parts", [])
                                    for part in parts:
                                        if "text" in part:
                                            logger.info(f"Found response in messages: {part['text']}")
                                            return part["text"]
                            
                            logger.error(f"Task completed but no text found in response")
                            return None
                        
                        elif status == "failed":
                            logger.error(f"Task {task_id} failed: {task}")
                            return None
                        
                        # Log status for debugging
                        if attempt % 5 == 0:  # Log every 5 attempts
                            logger.info(f"Task {task_id} status: {status} (attempt {attempt + 1})")
                            
                    else:
                        logger.error(f"No result in poll response: {result}")
                else:
                    logger.error(f"Poll request failed: {response.status_code} - {response.text}")
                
                # Wait before next poll
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error polling task {task_id}: {e}")
                return None
        
        logger.error(f"Task {task_id} timed out after {max_attempts} attempts")
        return None
    
    async def cancel(self, task_id: str) -> None:
        """
        Cancel a running task.
        
        Args:
            task_id: The ID of the task to cancel
        """
        # For now, we don't support cancellation
        logger.warning(f"Task cancellation requested for {task_id}, but not implemented")