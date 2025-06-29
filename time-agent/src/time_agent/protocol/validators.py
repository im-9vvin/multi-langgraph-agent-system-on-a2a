"""Protocol validation utilities."""

import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from .models import A2AMessage, TimeRequest


class ProtocolValidator:
    """Validates A2A protocol messages and time-specific requests."""
    
    # Common timezone patterns
    TIMEZONE_PATTERN = re.compile(r'^[A-Za-z]+/[A-Za-z_]+(?:/[A-Za-z_]+)?$')
    TIME_PATTERN = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    
    # Common timezone aliases
    TIMEZONE_ALIASES = {
        'EST': 'America/New_York',
        'PST': 'America/Los_Angeles',
        'GMT': 'UTC',
        'BST': 'Europe/London',
        'JST': 'Asia/Tokyo',
        'CST': 'America/Chicago',
        'MST': 'America/Denver',
    }
    
    @classmethod
    def validate_a2a_message(cls, message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate A2A protocol message format.
        
        Args:
            message: Raw message dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            A2AMessage(**message)
            return True, None
        except ValidationError as e:
            return False, str(e)
    
    @classmethod
    def validate_timezone(cls, timezone: str) -> Tuple[bool, Optional[str]]:
        """Validate timezone format and convert aliases.
        
        Args:
            timezone: Timezone string
            
        Returns:
            Tuple of (is_valid, normalized_timezone_or_error)
        """
        # Check for common aliases
        if timezone.upper() in cls.TIMEZONE_ALIASES:
            return True, cls.TIMEZONE_ALIASES[timezone.upper()]
        
        # Validate IANA format
        if cls.TIMEZONE_PATTERN.match(timezone):
            return True, timezone
        
        return False, f"Invalid timezone format: {timezone}"
    
    @classmethod
    def validate_time_format(cls, time: str) -> Tuple[bool, Optional[str]]:
        """Validate time format (HH:MM).
        
        Args:
            time: Time string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if cls.TIME_PATTERN.match(time):
            return True, None
        
        return False, f"Invalid time format: {time}. Use HH:MM format."
    
    @classmethod
    def extract_time_request(cls, messages: List[Dict[str, Any]]) -> Optional[TimeRequest]:
        """Extract time request from conversation messages.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            TimeRequest if extractable, None otherwise
        """
        if not messages:
            return None
        
        # Get the last user message
        last_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "").lower()
                break
        
        if not last_message:
            return None
        
        # Simple pattern matching for time requests
        if "what time" in last_message or "current time" in last_message:
            # Extract timezone if mentioned
            timezone = cls._extract_timezone_from_text(last_message)
            return TimeRequest(
                operation="current_time",
                timezone=timezone
            )
        
        elif "convert" in last_message and ("time" in last_message or "timezone" in last_message):
            # This would need more sophisticated parsing in production
            return TimeRequest(operation="convert_time")
        
        return None
    
    @classmethod
    def _extract_timezone_from_text(cls, text: str) -> Optional[str]:
        """Extract timezone from natural language text.
        
        Args:
            text: Input text
            
        Returns:
            Extracted timezone or None
        """
        # Look for common patterns like "in Tokyo" or "in New York"
        import re
        
        # Common city to timezone mappings
        city_timezones = {
            'tokyo': 'Asia/Tokyo',
            'new york': 'America/New_York',
            'london': 'Europe/London',
            'paris': 'Europe/Paris',
            'sydney': 'Australia/Sydney',
            'los angeles': 'America/Los_Angeles',
            'chicago': 'America/Chicago',
            'singapore': 'Asia/Singapore',
            'hong kong': 'Asia/Hong_Kong',
            'berlin': 'Europe/Berlin',
        }
        
        # Try to find city names
        for city, tz in city_timezones.items():
            if city in text.lower():
                return tz
        
        # Try to find timezone abbreviations
        for abbr, tz in cls.TIMEZONE_ALIASES.items():
            if abbr.lower() in text.lower():
                return tz
        
        return None