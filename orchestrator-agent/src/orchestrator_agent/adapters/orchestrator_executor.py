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
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from a2a.utils import new_task
from a2a.utils.errors import ServerError

# Internal imports
from ..common import get_logger
from ..common.config import config
from ..core.agent import create_orchestrator_agent, get_llm
from ..core.state import OrchestratorState
from ..core.prompts import ERROR_HANDLE_PROMPT
from ..subsystems import CheckpointManager, StreamingHandler, ProtocolHandler
from langchain_core.messages import HumanMessage, SystemMessage
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
        
        # Initialize subsystems
        self.checkpoint_manager = CheckpointManager()
        self.streaming_handler = StreamingHandler()
        self.protocol_handler = ProtocolHandler()
        
        # Create LangGraph orchestrator with checkpoint support
        self.orchestrator = create_orchestrator_agent(
            checkpointer=self.checkpoint_manager.get_saver()
        )
        
        # Flag to track if agents have been discovered
        self._agents_discovered = False
        
    async def _ensure_agents_discovered(self):
        """Ensure agents are discovered before first use."""
        if not self._agents_discovered:
            default_agents = config.get_remote_agents()
            logger.info(f"Discovering agents: {default_agents}")
            await agent_registry.discover_multiple(default_agents)
            self._agents_discovered = True
    
    def _generate_context_aware_message(self, query: str, phase: str, agent_info: dict = None) -> str:
        """Generate context-aware progress message based on query and phase.
        
        Args:
            query: User query
            phase: Current processing phase
            agent_info: Optional agent information for specific messages
            
        Returns:
            Context-aware message
        """
        import re
        
        # Split query into words (handle both Korean and English)
        # Korean: split by spaces and particles
        # English: split by spaces
        words = re.findall(r'[가-힣]+|[A-Za-z]+|\d+', query)
        
        # Get first 3 words or less
        if len(words) > 3:
            preview = ' '.join(words[:3]) + '...'
        else:
            preview = ' '.join(words)
        
        # Generate phase-specific messages with preview
        if phase == "initializing":
            return f"🔍 메시지를 받았습니다: '{preview}'"
            
        elif phase == "chain_start":
            return f"🚀 '{preview}'에 대해 판단중..."
            
        elif phase == "plan_complete":
            # Check if multiple agents involved
            if agent_info and "agent_count" in agent_info:
                count = agent_info["agent_count"]
                if count > 1:
                    return f"📋 '{preview}' {count}개 응답 계획을 수립했습니다..."
            return f"📋 '{preview}' 어떻게 답할지 생각중..."
            
        elif phase == "route_complete":
            # Show which agents were selected
            if agent_info and "agents" in agent_info:
                agents = agent_info["agents"]
                if len(agents) > 1:
                    agent_names = ", ".join(agents)
                    return f"🔀 '{preview}' {agent_names} 선택 완료..."
                elif len(agents) == 1:
                    return f"🔀 '{preview}' {agents[0]} 선택 완료..."
            return f"🔀 '{preview}' 적절한 에이전트를 선택했습니다..."
            
        elif phase == "execute_complete":
            # Show which agent completed
            if agent_info and "agent_name" in agent_info:
                return f"📥 {agent_info['agent_name']}로부터 정보를 받았습니다..."
            return f"📥 '{preview}' 정보를 수집했습니다..."
            
        elif phase == "aggregate_complete":
            # Show if multiple results were aggregated
            if agent_info and "result_count" in agent_info:
                count = agent_info["result_count"]
                if count > 1:
                    return f"📝 {count}개 결과를 종합하여 최종 답변을 준비했습니다..."
            return f"📝 '{preview}' 최종 결과를 준비했습니다..."
            
        # Default fallback
        return "⚡ 처리 중입니다..."
    
    def _extract_agent_name(self, agent_url: str, message: str = "") -> str:
        """Extract agent name from agent registry.
        
        Args:
            agent_url: Agent URL
            message: Task message (not used)
            
        Returns:
            Agent name from card or fallback
        """
        # Get agent info from registry
        agent_info = agent_registry.agents.get(agent_url)
        if agent_info:
            return agent_info.get("name", "에이전트")
        
        # Fallback if not in registry
        import re
        if ":" in agent_url:
            port_match = re.search(r':(\d+)', agent_url)
            if port_match:
                return f"에이전트-{port_match.group(1)}"
        
        return "에이전트"
    
    async def _generate_error_message(self, user_request: str, error_type: str, error_detail: str, failed_operation: str) -> str:
        """Generate a dynamic error message using LLM."""
        try:
            llm = get_llm()
            prompt = ERROR_HANDLE_PROMPT.format(
                user_request=user_request,
                error_type=error_type,
                error_detail=error_detail,
                failed_operation=failed_operation
            )
            
            response = await llm.ainvoke([
                SystemMessage(content="당신은 친절하고 도움이 되는 AI 비서입니다."),
                HumanMessage(content=prompt)
            ])
            
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate error message: {e}")
            # Fallback to a simple error message
            return "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        
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
            
            # Update task status to working with context-aware initial message
            initial_message = self._generate_context_aware_message(query, "initializing")
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message(
                    [Part(root=TextPart(text=initial_message))],
                    metadata={"type": "progress", "phase": "initializing"}
                )
            )
            
            # Handle request directly, not in background
            await self._handle_request(query, sdk_task.contextId, updater)
            
        except Exception as e:
            logger.error("Orchestration failed", error=str(e))
            error_message = await self._generate_error_message(
                user_request=query,
                error_type=type(e).__name__,
                error_detail=str(e),
                failed_operation="오케스트레이션 실행"
            )
            await updater.add_artifact(
                [Part(root=TextPart(text=error_message))],
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
            # Always use LangGraph orchestrator for ALL queries
            # This ensures prompts.py is used for greetings and meta questions too
            response = await self._orchestrate_with_langgraph(query, context_id, updater)
            
            # Send final response
            await updater.add_artifact(
                [Part(root=TextPart(text=response))],
                name="response.txt"
            )
            
            # Complete the task
            await updater.complete()
            
        except Exception as e:
            logger.error(f"Request handling failed: {e}")
            error_message = await self._generate_error_message(
                user_request=query,
                error_type=type(e).__name__,
                error_detail=str(e),
                failed_operation="요청 처리"
            )
            await updater.add_artifact(
                [Part(root=TextPart(text=error_message))],
                name="error.txt"
            )
            await updater.update_status(TaskState.failed)
    
    async def _orchestrate_with_langgraph(self, query: str, context_id: str, updater: TaskUpdater) -> str:
        """
        Orchestrate using LangGraph with LLM-based routing.
        
        Args:
            query: User query
            context_id: Context ID
            updater: Task updater for progress updates
            
        Returns:
            Final orchestrated response
        """
        try:
            # Create protocol task
            task_msg = self.protocol_handler.create_task_message(query, context_id)
            
            # Run orchestrator
            logger.info(f"Running LangGraph orchestrator for query: {query} with context_id: {context_id}")
            config = {"configurable": {"thread_id": context_id}}
            
            # Get the latest state from checkpoint
            checkpoint_tuple = await self.checkpoint_manager.get_saver().aget_tuple(config)
            
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                # Use existing state and append new message
                checkpoint_data = checkpoint_tuple.checkpoint
                # The checkpoint data should be the state dictionary
                if isinstance(checkpoint_data, dict) and "messages" in checkpoint_data:
                    # Found valid checkpoint with messages
                    initial_state = checkpoint_data.copy()
                    initial_state["messages"].append(HumanMessage(content=query))
                    initial_state["phase"] = "planning"
                    initial_state["plan"] = None
                    initial_state["routing_decision"] = None
                    initial_state["remote_calls"] = []
                    initial_state["aggregated_results"] = None
                    initial_state["error"] = None
                else:
                    # Invalid checkpoint format, create new state
                    logger.warning(f"Invalid checkpoint format: {checkpoint_data}")
                    initial_state = {
                        "messages": [HumanMessage(content=query)],
                        "phase": "planning",
                        "plan": None,
                        "routing_decision": None,
                        "remote_calls": [],
                        "aggregated_results": None,
                        "error": None,
                        "context_id": context_id
                    }
            else:
                # Create initial state for new conversation
                initial_state = {
                    "messages": [HumanMessage(content=query)],
                    "phase": "planning",
                    "plan": None,
                    "routing_decision": None,
                    "remote_calls": [],
                    "aggregated_results": None,
                    "error": None,
                    "context_id": context_id
                }
            
            # Store updater in config for access during streaming
            config["configurable"]["task_updater"] = updater
            
            # Use astream_events for more detailed real-time updates
            final_state = None
            try:
                # Try to use astream_events if available
                async for event in self.orchestrator.astream_events(initial_state, config, version="v1"):
                    # Log the event with more detail
                    logger.info(f"LangGraph event type: {event.get('event')} - name: {event.get('name')} - data keys: {list(event.get('data', {}).keys()) if 'data' in event else 'no data'}")
                    
                    # Handle different event types
                    if event["event"] == "on_chain_start" and event["name"] == "LangGraph":
                        chain_start_msg = self._generate_context_aware_message(query, "chain_start")
                        # Add [E] indicator for event streaming messages
                        chain_start_msg = f"[E] {chain_start_msg}"
                        await updater.update_status(
                            TaskState.working,
                            message=updater.new_agent_message(
                                [Part(root=TextPart(text=chain_start_msg))],
                                metadata={"type": "progress", "phase": "chain_start", "source": "event_stream"}
                            )
                        )
                    
                    # Check for on_chain_end events which contain node outputs
                    elif event["event"] == "on_chain_end" and event.get("name") in ["plan", "route", "execute", "aggregate"]:
                        # This contains the actual node outputs - check different possible data structures
                        chunk = event.get("data", {})
                        
                        # Sometimes the chunk is directly in data
                        if "chunk" in chunk:
                            chunk = chunk["chunk"]
                        
                        # Sometimes it's in output
                        if "output" in chunk and isinstance(chunk["output"], dict):
                            chunk = chunk["output"]
                        
                        # Get node name from event
                        node_name = event.get("name", "")
                        node_output = chunk.get("output", chunk) if isinstance(chunk, dict) else chunk
                        
                        if node_name in ["plan", "route", "execute", "aggregate"]:
                            logger.info(f"LangGraph node completed: {node_name}")
                            
                            # Send completion updates for each node with context-aware messages
                            if node_name == "plan":
                                # For plan node, we don't have routing_decision yet
                                agent_info = {}
                                
                                plan_msg = self._generate_context_aware_message(query, "plan_complete", agent_info)
                                # Add [E] indicator for event streaming messages
                                plan_msg = f"[E] {plan_msg}"
                                await updater.update_status(
                                    TaskState.working,
                                    message=updater.new_agent_message(
                                        [Part(root=TextPart(text=plan_msg))],
                                        metadata={"type": "progress", "phase": "plan_complete", "node": node_name, "source": "event_stream"}
                                    )
                                )
                            elif node_name == "route":
                                # Extract agent names from routing decision
                                agent_info = {"agents": [], "agent_count": 0}
                                if isinstance(node_output, dict) and "routing_decision" in node_output:
                                    tasks = node_output["routing_decision"].get("tasks", [])
                                    agent_info["agent_count"] = len(tasks)
                                    for task in tasks:
                                        # Try to extract meaningful agent name from URL or message
                                        agent_url = task.get("agent_url", "")
                                        message = task.get("message", "")
                                        
                                        # Extract from URL pattern or message content
                                        agent_name = self._extract_agent_name(agent_url, message)
                                        agent_info["agents"].append(agent_name)
                                
                                route_msg = self._generate_context_aware_message(query, "route_complete", agent_info)
                                # Add [E] indicator for event streaming messages
                                route_msg = f"[E] {route_msg}"
                                await updater.update_status(
                                    TaskState.working,
                                    message=updater.new_agent_message(
                                        [Part(root=TextPart(text=route_msg))],
                                        metadata={"type": "progress", "phase": "route_complete", "node": node_name, "source": "event_stream"}
                                    )
                                )
                            elif node_name == "execute":
                                # Count completed calls
                                agent_info = {}
                                if isinstance(node_output, dict) and "remote_calls" in node_output:
                                    completed = [c for c in node_output["remote_calls"] if c.get("status") == "completed"]
                                    if completed:
                                        # Get last completed agent
                                        last_call = completed[-1]
                                        agent_url = last_call.get("agent_url", "")
                                        # Try to get task message for context
                                        task_message = ""
                                        if "routing_decision" in node_output:
                                            tasks = node_output["routing_decision"].get("tasks", [])
                                            for task in tasks:
                                                if task.get("agent_url") == agent_url:
                                                    task_message = task.get("message", "")
                                                    break
                                        
                                        agent_info["agent_name"] = self._extract_agent_name(agent_url, task_message)
                                
                                exec_msg = self._generate_context_aware_message(query, "execute_complete", agent_info)
                                # Add [E] indicator for event streaming messages
                                exec_msg = f"[E] {exec_msg}"
                                await updater.update_status(
                                    TaskState.working,
                                    message=updater.new_agent_message(
                                        [Part(root=TextPart(text=exec_msg))],
                                        metadata={"type": "progress", "phase": "execute_complete", "node": node_name, "source": "event_stream"}
                                    )
                                )
                            elif node_name == "aggregate":
                                # Count results
                                agent_info = {}
                                if isinstance(node_output, dict) and "remote_calls" in node_output:
                                    results = [c for c in node_output["remote_calls"] if c.get("result")]
                                    agent_info["result_count"] = len(results)
                                
                                agg_msg = self._generate_context_aware_message(query, "aggregate_complete", agent_info)
                                # Add [E] indicator for event streaming messages
                                agg_msg = f"[E] {agg_msg}"
                                await updater.update_status(
                                    TaskState.working,
                                    message=updater.new_agent_message(
                                        [Part(root=TextPart(text=agg_msg))],
                                        metadata={"type": "progress", "phase": "aggregate_complete", "node": node_name, "source": "event_stream"}
                                    )
                                )
                            
                            # Keep track of state
                            if isinstance(node_output, dict):
                                final_state = node_output
                    
                    elif event["event"] == "on_chain_end":
                        # Final output
                        outputs = event.get("data", {}).get("output", {})
                        if outputs:
                            final_state = outputs
                            
            except AttributeError:
                # Fallback to regular astream if astream_events is not available
                logger.info("astream_events not available, falling back to astream")
                async for chunk in self.orchestrator.astream(initial_state, config):
                    for node_name, node_output in chunk.items():
                        logger.info(f"LangGraph node executed: {node_name}")
                        
                        # Use dynamic context-aware messages in fallback too
                        if node_name in ["plan", "route", "execute", "aggregate"]:
                            # Extract necessary info for context-aware messages
                            agent_info = {}
                            
                            if node_name == "plan" and isinstance(node_output, dict):
                                # For plan node, we don't have routing_decision yet
                                # We'll get the count in the route node
                                agent_info = {}
                            
                            elif node_name == "route" and isinstance(node_output, dict) and "routing_decision" in node_output:
                                tasks = node_output["routing_decision"].get("tasks", [])
                                agent_info["agents"] = []
                                agent_info["agent_count"] = len(tasks)
                                for task in tasks:
                                    agent_url = task.get("agent_url", "")
                                    agent_name = self._extract_agent_name(agent_url, "")
                                    agent_info["agents"].append(agent_name)
                            
                            elif node_name == "execute" and isinstance(node_output, dict) and "remote_calls" in node_output:
                                completed = [c for c in node_output["remote_calls"] if c.get("status") == "completed"]
                                if completed:
                                    last_call = completed[-1]
                                    agent_url = last_call.get("agent_url", "")
                                    agent_info["agent_name"] = self._extract_agent_name(agent_url, "")
                            
                            elif node_name == "aggregate" and isinstance(node_output, dict) and "remote_calls" in node_output:
                                results = [c for c in node_output["remote_calls"] if c.get("result")]
                                agent_info["result_count"] = len(results)
                            
                            # Generate context-aware message with fallback indicator
                            phase = f"{node_name}_complete"
                            status_text = self._generate_context_aware_message(query, phase, agent_info)
                            # Add [F] indicator for fallback messages
                            status_text = f"[F] {status_text}"
                            
                            await updater.update_status(
                                TaskState.working,
                                message=updater.new_agent_message(
                                    [Part(root=TextPart(text=status_text))],
                                    metadata={"type": "progress", "phase": phase, "source": "fallback"}
                                )
                            )
                        
                        if isinstance(node_output, dict):
                            final_state = node_output
            
            if not final_state:
                # If no state was captured, run ainvoke as fallback
                logger.warning("No state captured from streaming, falling back to ainvoke")
                final_state = await self.orchestrator.ainvoke(initial_state, config)
            
            # Handle different final state structures
            actual_state = final_state
            
            # Check if state is wrapped in a node name (like 'aggregate')
            if final_state and len(final_state) == 1:
                node_name = list(final_state.keys())[0]
                if isinstance(final_state[node_name], dict) and "messages" in final_state[node_name]:
                    logger.info(f"State wrapped in node: {node_name}")
                    actual_state = final_state[node_name]
            
            logger.info(f"Final orchestrator state phase: {actual_state.get('phase') if isinstance(actual_state, dict) else 'unknown'}")
            
            # Check aggregated results first (highest priority)
            if actual_state and isinstance(actual_state, dict) and "aggregated_results" in actual_state and actual_state["aggregated_results"]:
                response = actual_state["aggregated_results"].get("response", "")
                if response:
                    logger.info(f"Found aggregated response: {response}")
                    return response
            
            # Extract final response from messages
            if actual_state and isinstance(actual_state, dict) and "messages" in actual_state:
                for msg in reversed(actual_state["messages"]):
                    if hasattr(msg, "content") and hasattr(msg, "type"):
                        if msg.type == "ai":  # AIMessage from aggregation
                            logger.info(f"Found AI response: {msg.content}")
                            return msg.content
            
            # Check remote calls for direct results
            if actual_state and isinstance(actual_state, dict) and "remote_calls" in actual_state:
                results = []
                for call in actual_state["remote_calls"]:
                    if call.get("status") == "completed" and call.get("result"):
                        results.append(call["result"])
                if results:
                    return "\n".join(results)
            
            logger.error(f"No response found in final state: {final_state}")
            error_msg = await self._generate_error_message(
                user_request=query,
                error_type="NoResponseError",
                error_detail="최종 상태에서 응답을 찾을 수 없음",
                failed_operation="응답 생성"
            )
            
            # Update protocol task
            self.protocol_handler.create_error_message(
                task_msg.task_id, error_msg, "NoResponseError"
            )
            
            return error_msg
            
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
            
            else:
                # Default: try general agent
                response = await self._call_agent("http://localhost:10001", query, context_id)
                if response:
                    return response
                    
            return await self._generate_error_message(
                user_request=query,
                error_type="RequestFailure",
                error_detail="모든 에이전트가 응답하지 않음",
                failed_operation="에이전트 호출"
            )
    
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
            error_message = await self._generate_error_message(
                user_request=query,
                error_type=type(e).__name__,
                error_detail=str(e),
                failed_operation="오케스트레이션 처리"
            )
            await updater.add_artifact(
                [Part(root=TextPart(text=error_message))],
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
                return await self._generate_error_message(
                    user_request=query,
                    error_type="ServiceUnavailable",
                    error_detail="환율 서비스 응답 없음",
                    failed_operation="환율 정보 조회"
                )
            elif any(keyword in query_lower for keyword in time_keywords):
                return await self._generate_error_message(
                    user_request=query,
                    error_type="ServiceUnavailable",
                    error_detail="시간 서비스 응답 없음",
                    failed_operation="시간 정보 조회"
                )
            else:
                return await self._generate_error_message(
                    user_request=query,
                    error_type="NoResultFound",
                    error_detail="적절한 에이전트를 찾을 수 없음",
                    failed_operation="에이전트 라우팅"
                )
    
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
    
    async def _stream_orchestration_progress(self, context_id: str, task_id: str, updater: TaskUpdater):
        """Stream orchestration progress events with status updates.
        
        Args:
            context_id: Context ID
            task_id: Protocol task ID
            updater: Task updater for sending status messages
        """
        try:
            # Publish initial event
            await self.streaming_handler.publish_orchestration_event(
                context_id, "started", {"task_id": task_id}
            )
            
            # Phase-specific status messages in Korean
            phase_messages = {
                "planning": "📋 요청을 분석하고 실행 계획을 수립하고 있습니다...",
                "routing": "🔀 적절한 에이전트를 선택하고 있습니다...",
                "executing": "⚡ 에이전트에게 작업을 요청하고 있습니다...",
                "aggregating": "📊 결과를 종합하고 있습니다..."
            }
            
            # Monitor LangGraph stream if available
            # For now, just publish periodic progress
            phases = ["planning", "routing", "executing", "aggregating"]
            for i, phase in enumerate(phases):
                await asyncio.sleep(0.5)  # Simulate progress
                
                # Send status update to user
                if phase in phase_messages:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=phase_messages[phase]))],
                        name="status_update.txt"
                    )
                
                await self.streaming_handler.publish_orchestration_event(
                    context_id, "progress", {
                        "phase": phase,
                        "progress": (i + 1) / len(phases) * 100
                    }
                )
                
                # Update protocol task progress
                self.protocol_handler.create_progress_message(
                    task_id, {"phase": phase, "progress": (i + 1) / len(phases) * 100}
                )
        except Exception as e:
            logger.error(f"Error streaming progress: {e}")
    
    async def get_stream_endpoint(self, context_id: str):
        """Get SSE endpoint for streaming.
        
        Args:
            context_id: Context ID
            
        Returns:
            SSE generator function
        """
        return self.streaming_handler.create_sse_endpoint(context_id)
    
    async def execute_stream(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute an A2A streaming request.
        
        This method handles the message/stream endpoint, sending real-time
        status updates and progress events via Server-Sent Events (SSE).
        
        Args:
            context: Request context containing user input and task info
            event_queue: A2A event queue for sending SSE events to client
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
            
            # Send initial task status update via SSE with context-aware message
            from a2a.types import TaskStatus
            initial_sse_msg = self._generate_context_aware_message(query, "initializing")
            status_event = TaskStatusUpdateEvent(
                taskId=sdk_task.id,
                contextId=sdk_task.contextId,
                kind="status-update",
                status=TaskStatus(state=TaskState.working, message=initial_sse_msg),
                final=False
            )
            await event_queue.enqueue_event(status_event)
            
            # Handle request with streaming updates
            await self._handle_request_with_streaming(query, sdk_task.contextId, updater, event_queue)
            
        except Exception as e:
            logger.error("Orchestration failed", error=str(e))
            error_message = await self._generate_error_message(
                user_request=query,
                error_type=type(e).__name__,
                error_detail=str(e),
                failed_operation="오케스트레이션 실행"
            )
            
            # Send error as final artifact
            await updater.add_artifact(
                [Part(root=TextPart(text=error_message))],
                name="error.txt"
            )
            
            # Send final status update
            from a2a.types import TaskStatus
            final_status = TaskStatusUpdateEvent(
                taskId=sdk_task.id,
                contextId=sdk_task.contextId,
                kind="status-update",
                status=TaskStatus(state=TaskState.failed),
                final=True
            )
            await event_queue.enqueue_event(final_status)
    
    async def _handle_request_with_streaming(self, query: str, context_id: str, updater: TaskUpdater, event_queue: EventQueue) -> None:
        """
        Handle request with SSE streaming updates.
        
        Args:
            query: User query
            context_id: Context ID
            updater: Task updater
            event_queue: Event queue for SSE
        """
        try:
            # Create a custom updater that sends SSE events
            class StreamingTaskUpdater:
                def __init__(self, base_updater: TaskUpdater, event_queue: EventQueue, task_id: str, context_id: str):
                    self.base_updater = base_updater
                    self.event_queue = event_queue
                    self.task_id = task_id
                    self.context_id = context_id
                
                async def update_status(self, state: TaskState, message=None):
                    """Send status update via SSE."""
                    if message and hasattr(message, 'parts') and message.parts:
                        # Extract text from message parts
                        text = ""
                        for part in message.parts:
                            if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                text = part.root.text
                                break
                        
                        # Send SSE status update
                        from a2a.types import TaskStatus
                        status_event = TaskStatusUpdateEvent(
                            taskId=self.task_id,
                            contextId=self.context_id,
                            kind="status-update",
                            status=TaskStatus(state=state, message=text),
                            final=False
                        )
                        await self.event_queue.enqueue_event(status_event)
                    
                    # Also update via base updater
                    return await self.base_updater.update_status(state, message)
                
                def __getattr__(self, name):
                    """Forward other methods to base updater."""
                    return getattr(self.base_updater, name)
            
            # Create streaming updater
            streaming_updater = StreamingTaskUpdater(updater, event_queue, updater.task_id, context_id)
            
            # Run orchestration with streaming updater
            response = await self._orchestrate_with_langgraph(query, context_id, streaming_updater)
            
            # Send final response
            await updater.add_artifact(
                [Part(root=TextPart(text=response))],
                name="response.txt"
            )
            
            # Send final status update
            from a2a.types import TaskStatus
            final_status = TaskStatusUpdateEvent(
                taskId=updater.task_id,
                contextId=context_id,
                kind="status-update",
                status=TaskStatus(state=TaskState.completed),
                final=True
            )
            await event_queue.enqueue_event(final_status)
            
        except Exception as e:
            logger.error(f"Request handling failed: {e}")
            error_message = await self._generate_error_message(
                user_request=query,
                error_type=type(e).__name__,
                error_detail=str(e),
                failed_operation="요청 처리"
            )
            await updater.add_artifact(
                [Part(root=TextPart(text=error_message))],
                name="error.txt"
            )
            
            # Send final failed status
            from a2a.types import TaskStatus
            final_status = TaskStatusUpdateEvent(
                taskId=updater.task_id,
                contextId=context_id,
                kind="status-update",
                status=TaskStatus(state=TaskState.failed),
                final=True
            )
            await event_queue.enqueue_event(final_status)
    
    async def cancel(self, task_id: str) -> None:
        """
        Cancel a running task.
        
        Args:
            task_id: The ID of the task to cancel
        """
        # For now, we don't support cancellation
        logger.warning(f"Task cancellation requested for {task_id}, but not implemented")