"""Tools for orchestrating remote A2A agents."""

import json
from typing import Any, Optional

import httpx
from langchain_core.tools import tool

from ..common import get_logger
from ..common.config import config
from ..common.exceptions import RemoteAgentError

logger = get_logger(__name__)


@tool
async def query_agent_capabilities(agent_url: str) -> dict[str, Any]:
    """Query an agent's capabilities via its agent card.
    
    Args:
        agent_url: The base URL of the agent
        
    Returns:
        The agent's capabilities from its agent card
    """
    try:
        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            response = await client.get(f"{agent_url}/.well-known/agent.json")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error("Failed to query agent capabilities", agent_url=agent_url, error=str(e))
        raise RemoteAgentError(agent_url, f"Failed to query capabilities: {e}")


@tool
async def send_task_to_agent(
    agent_url: str, 
    message: str,
    context_id: Optional[str] = None
) -> dict[str, Any]:
    """Send a task to a remote A2A agent.
    
    Args:
        agent_url: The base URL of the agent
        message: The message to send to the agent
        context_id: Optional context ID for conversation continuity
        
    Returns:
        The task creation response from the agent
    """
    try:
        # Create A2A message
        a2a_message = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": f"orch-{hash(message) % 10000}",
                    "role": "user",
                    "parts": [{"text": message}],
                    "contextId": context_id or "orchestration"
                }
            },
            "id": 1
        }
        
        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            response = await client.post(
                agent_url,  # A2A agents accept requests at base URL
                json=a2a_message,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            if "error" in result:
                raise RemoteAgentError(agent_url, f"Agent returned error: {result['error']}")
                
            # Return the task info with ID
            task_result = result.get("result", {})
            task_id = task_result.get("id") or task_result.get("taskId")
            
            return {
                "taskId": task_id,
                "contextId": task_result.get("contextId", context_id),
                "status": task_result.get("status", {}),
                "raw": task_result
            }
            
    except httpx.HTTPError as e:
        logger.error("HTTP error calling agent", agent_url=agent_url, error=str(e))
        raise RemoteAgentError(agent_url, f"HTTP error: {e}")
    except Exception as e:
        logger.error("Failed to send task to agent", agent_url=agent_url, error=str(e))
        raise RemoteAgentError(agent_url, f"Failed to send task: {e}")


@tool
async def check_task_status(agent_url: str, task_id: str) -> dict[str, Any]:
    """Check the status of a task on a remote agent.
    
    Args:
        agent_url: The base URL of the agent
        task_id: The ID of the task to check
        
    Returns:
        The current task status
    """
    try:
        # Use JSON-RPC for task status
        poll_data = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"id": task_id},
            "id": 2
        }
        
        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            response = await client.post(
                agent_url,
                json=poll_data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            if "result" in result:
                return result["result"]
            else:
                return result
    except Exception as e:
        logger.error("Failed to check task status", agent_url=agent_url, task_id=task_id, error=str(e))
        raise RemoteAgentError(agent_url, f"Failed to check task {task_id}: {e}")


@tool  
async def wait_for_task_completion(
    agent_url: str, 
    task_id: str,
    max_polls: int = 30,
    poll_interval: float = 1.0
) -> dict[str, Any]:
    """Wait for a task to complete on a remote agent.
    
    Args:
        agent_url: The base URL of the agent
        task_id: The ID of the task to wait for
        max_polls: Maximum number of status checks
        poll_interval: Seconds between status checks
        
    Returns:
        The completed task with results
    """
    import asyncio
    
    for i in range(max_polls):
        try:
            task_status = await check_task_status(agent_url, task_id)
            
            # Check A2A task status format
            status_state = task_status.get("status", {}).get("state")
            if status_state in ["completed", "failed", "cancelled"]:
                return task_status
                
            # Wait before next poll
            if i < max_polls - 1:
                await asyncio.sleep(poll_interval)
                
        except Exception as e:
            logger.error("Error polling task", agent_url=agent_url, task_id=task_id, error=str(e))
            if i == max_polls - 1:
                raise
                
    raise RemoteAgentError(agent_url, f"Task {task_id} did not complete within timeout")


@tool
def parse_agent_results(task_result: dict[str, Any]) -> str:
    """Parse and format results from an agent task.
    
    Args:
        task_result: The task result from an agent
        
    Returns:
        Formatted string representation of the results
    """
    try:
        status_state = task_result.get("status", {}).get("state")
        if status_state == "failed":
            return f"Task failed: {task_result.get('error', 'Unknown error')}"
            
        # Check for artifacts array
        artifacts = task_result.get("artifacts", [])
        if not artifacts:
            # Check for single artifact
            artifact = task_result.get("artifact")
            if artifact:
                artifacts = [artifact]
            else:
                return "No results returned from agent"
            
        # Extract text from artifacts
        results = []
        for artifact in artifacts:
            if "parts" in artifact:
                for part in artifact["parts"]:
                    if isinstance(part, dict) and "text" in part:
                        results.append(part["text"])
                    elif part.get("kind") == "text" and "text" in part:
                        results.append(part["text"])
                
        return "\n".join(results) if results else "No text results found"
        
    except Exception as e:
        logger.error("Failed to parse agent results", error=str(e))
        return f"Error parsing results: {e}"