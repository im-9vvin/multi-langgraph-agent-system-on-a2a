# Standard library imports
from typing import Any, Dict

# Third-party library imports
import httpx

# LangChain imports
from langchain_core.tools import tool


@tool
def get_exchange_rate(
    currency_from: str = 'USD',
    currency_to: str = 'EUR',
    currency_date: str = 'latest',
) -> Dict[str, Any]:
    """
    Get current exchange rate using Frankfurter API.
    
    This function retrieves real-time exchange rate information
    and is wrapped as a LangChain tool for agent use.

    Args:
        currency_from: Source currency code (e.g., "USD")
        currency_to: Target currency code (e.g., "EUR")  
        currency_date: Exchange rate date or "latest"

    Returns:
        Dictionary containing exchange rate data or error message
    """
    try:
        response = httpx.get(
            f'https://api.frankfurter.app/{currency_date}',
            params={'from': currency_from, 'to': currency_to},
        )
        response.raise_for_status()

        data = response.json()
        if 'rates' not in data:
            return {'error': 'Invalid API response format.'}
        return data
    except httpx.HTTPError as e:
        return {'error': f'API request failed: {e}'}
    except ValueError:
        return {'error': 'Invalid JSON response from API.'}