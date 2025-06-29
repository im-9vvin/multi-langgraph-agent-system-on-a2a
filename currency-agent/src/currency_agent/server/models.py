# A2A protocol imports
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

# Internal imports
from ..core.agent import CurrencyAgent


def create_agent_card(host: str, port: int) -> AgentCard:
    """
    Create the A2A agent card for the currency agent.
    
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
    
    # Define agent skill
    skill = AgentSkill(
        id='convert_currency',
        name='Currency Exchange Rates Tool',
        description='Helps with exchange values between various currencies',
        tags=['currency conversion', 'currency exchange'],
        examples=['What is exchange rate between USD and GBP?'],
    )
    
    # Create and return agent card
    return AgentCard(
        name='Currency Agent',
        description='Helps with exchange rates for currencies',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )