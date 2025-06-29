"""Server models for A2A compliance."""

# A2A protocol imports
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

# Internal imports
from ..common.config import config


def create_agent_card(host: str, port: int) -> AgentCard:
    """
    Create the A2A agent card for the orchestrator agent.
    
    Args:
        host: Server host address
        port: Server port number
        
    Returns:
        AgentCard: Configured agent card with metadata
    """
    # Define agent capabilities
    capabilities = AgentCapabilities(
        streaming=True,
        pushNotifications=True
    )
    
    # Define agent skills
    skills = [
        AgentSkill(
            id='orchestrate_tasks',
            name='Multi-Agent Orchestration',
            description='Orchestrates tasks across multiple specialized agents',
            tags=['orchestration', 'multi-agent', 'task-routing'],
            examples=[
                'What is the USD to EUR rate and tell me about Python?',
                'Convert 100 USD to EUR and explain REST APIs'
            ],
        ),
        AgentSkill(
            id='task_decomposition',
            name='Task Decomposition',
            description='Breaks down complex requests into sub-tasks for different agents',
            tags=['planning', 'decomposition', 'routing'],
            examples=['Analyze this complex request and route to appropriate agents'],
        ),
        AgentSkill(
            id='result_aggregation',
            name='Result Aggregation',
            description='Combines results from multiple agents into coherent responses',
            tags=['aggregation', 'synthesis', 'integration'],
            examples=['Combine these agent responses into a unified answer'],
        )
    ]
    
    # Create and return agent card
    return AgentCard(
        name='Orchestrator Agent',
        description='A2A Orchestrator that coordinates tasks across multiple specialized agents',
        url=f'http://{host}:{port}/',
        version='0.4.0',
        defaultInputModes=['text/plain'],
        defaultOutputModes=['text/plain'],
        capabilities=capabilities,
        skills=skills,
    )