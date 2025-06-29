#!/usr/bin/env -S uv run python
"""
Test client for the Currency Agent.

This script demonstrates how to interact with the Currency Agent
using the A2A protocol client.

Run with: uv run python src/currency_agent/client/test_client.py
"""

# Standard library imports
import asyncio
import logging
import sys
from typing import Optional

# Third-party imports
import click
import httpx
from a2a.client import A2AClient
from a2a.types import Message, Part, TaskState, TextPart


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_message(client: A2AClient, text: str, context_id: Optional[str] = None) -> str:
    """
    Send a message to the agent and get the response.
    
    Args:
        client: A2A client instance
        text: Message text to send
        context_id: Optional context ID for conversation continuity
        
    Returns:
        str: Agent's response or context ID for follow-up
    """
    # Create message parts
    parts = [Part(root=TextPart(text=text))]
    message = Message(
        role='user',
        parts=parts,
        contextId=context_id or 'test-context'
    )
    
    # Send message
    logger.info(f"Sending: {text}")
    response = await client.send_message(message)
    
    # Process response based on state
    if response.state == TaskState.completed:
        if response.artifact and response.artifact.parts:
            content = response.artifact.parts[0].root.text
            logger.info(f"Completed: {content}")
            return response.contextId
    elif response.state == TaskState.input_required:
        if response.message and response.message.parts:
            content = response.message.parts[0].root.text
            logger.info(f"Input required: {content}")
            return response.contextId
    elif response.state == TaskState.working:
        if response.message and response.message.parts:
            content = response.message.parts[0].root.text
            logger.info(f"Working: {content}")
            return response.contextId
    
    return response.contextId


async def interactive_session(base_url: str):
    """
    Run an interactive session with the agent.
    
    Args:
        base_url: Base URL of the agent server
    """
    httpx_client = httpx.AsyncClient(timeout=30.0)
    client = A2AClient(httpx_client=httpx_client, base_url=base_url)
    
    context_id = None
    
    try:
        # Get agent info
        agent_info = await client.get_agent_info()
        logger.info(f"Connected to: {agent_info.name}")
        logger.info(f"Description: {agent_info.description}")
        
        print("\nCurrency Agent Test Client")
        print("Type 'quit' to exit\n")
        
        while True:
            # Get user input
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                break
            
            if not user_input:
                continue
            
            # Send message and get response
            try:
                context_id = await send_message(client, user_input, context_id)
            except Exception as e:
                logger.error(f"Error: {e}")
                
    finally:
        await httpx_client.aclose()


async def test_examples(base_url: str):
    """
    Run example test queries.
    
    Args:
        base_url: Base URL of the agent server
    """
    httpx_client = httpx.AsyncClient(timeout=30.0)
    client = A2AClient(httpx_client=httpx_client, base_url=base_url)
    
    try:
        # Test queries
        queries = [
            "What is the exchange rate from USD to EUR?",
            "Convert 100 GBP to JPY",
            "What's the weather today?",  # Should be rejected
            "Show me USD to CHF rate for 2024-01-01"
        ]
        
        for query in queries:
            print(f"\n{'='*50}")
            await send_message(client, query)
            await asyncio.sleep(1)  # Brief pause between queries
            
    finally:
        await httpx_client.aclose()


@click.command()
@click.option('--url', default='http://localhost:10000', help='Agent server URL')
@click.option('--interactive', '-i', is_flag=True, help='Run in interactive mode')
def main(url: str, interactive: bool):
    """Test client for the Currency Agent."""
    if interactive:
        asyncio.run(interactive_session(url))
    else:
        asyncio.run(test_examples(url))


if __name__ == '__main__':
    main()