"""Time-related tools for the agent using MCP."""

import json
import os
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from langchain_core.tools import Tool

# For now, we'll create mock tools since MCP integration requires additional setup
# In production, this would use the actual MCP Time Server


class TimeTools:
    """Wrapper for time functionality."""
    
    def __init__(self, local_timezone: Optional[str] = None):
        """Initialize time tools.
        
        Args:
            local_timezone: Optional override for local timezone (IANA format)
        """
        self.local_timezone = local_timezone or os.environ.get("LOCAL_TIMEZONE", "UTC")
    
    async def get_current_time(self, timezone: str) -> Dict[str, Any]:
        """Get current time in a specific timezone.
        
        Args:
            timezone: IANA timezone name (e.g., 'America/New_York')
            
        Returns:
            Dict with datetime, timezone, and DST information
        """
        try:
            import pytz
            from datetime import datetime
            
            # Get timezone object
            tz = pytz.timezone(timezone)
            
            # Get current time
            now = datetime.now(tz)
            
            # Check if DST is active
            is_dst = bool(now.dst())
            
            return {
                "timezone": timezone,
                "datetime": {
                    "formatted": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "timezone_abbreviation": now.strftime("%Z"),
                    "iso": now.isoformat()
                },
                "is_dst": is_dst
            }
        except Exception as e:
            return {
                "error": f"Failed to get time for {timezone}: {str(e)}",
                "timezone": timezone
            }
    
    async def convert_time(
        self, 
        source_timezone: str, 
        time: str, 
        target_timezone: str
    ) -> Dict[str, Any]:
        """Convert time between timezones.
        
        Args:
            source_timezone: Source IANA timezone
            time: Time in 24-hour format (HH:MM)
            target_timezone: Target IANA timezone
            
        Returns:
            Dict with conversion details and time difference
        """
        try:
            import pytz
            from datetime import datetime, timedelta
            
            # Parse time
            hour, minute = map(int, time.split(':'))
            
            # Get timezones
            source_tz = pytz.timezone(source_timezone)
            target_tz = pytz.timezone(target_timezone)
            
            # Create datetime in source timezone (using today's date)
            now = datetime.now()
            source_dt = source_tz.localize(
                datetime(now.year, now.month, now.day, hour, minute)
            )
            
            # Convert to target timezone
            target_dt = source_dt.astimezone(target_tz)
            
            # Calculate time difference
            source_offset = source_dt.utcoffset().total_seconds() / 3600
            target_offset = target_dt.utcoffset().total_seconds() / 3600
            diff_hours = int(target_offset - source_offset)
            diff_minutes = int((target_offset - source_offset - diff_hours) * 60)
            
            return {
                "source": {
                    "timezone": source_timezone,
                    "time": source_dt.strftime("%H:%M"),
                    "date": source_dt.strftime("%Y-%m-%d"),
                    "timezone_abbreviation": source_dt.strftime("%Z")
                },
                "target": {
                    "timezone": target_timezone,
                    "time": target_dt.strftime("%H:%M"),
                    "date": target_dt.strftime("%Y-%m-%d"),
                    "timezone_abbreviation": target_dt.strftime("%Z")
                },
                "time_difference": {
                    "hours": abs(diff_hours),
                    "minutes": abs(diff_minutes),
                    "ahead": target_offset > source_offset
                }
            }
        except Exception as e:
            return {
                "error": f"Failed to convert time: {str(e)}",
                "source_timezone": source_timezone,
                "target_timezone": target_timezone,
                "time": time
            }
    
    async def cleanup(self):
        """Clean up resources."""
        # No cleanup needed for the simple implementation
        pass
    
    def get_langchain_tools(self) -> list[Tool]:
        """Get LangChain compatible tools.
        
        Returns:
            List of LangChain Tool objects
        """
        return [
            Tool(
                name="get_current_time",
                func=lambda timezone: self.get_current_time(timezone),
                coroutine=self.get_current_time,
                description=(
                    "Get the current time in a specific timezone. "
                    "Input should be an IANA timezone name like 'America/New_York' or 'Europe/London'."
                )
            ),
            Tool(
                name="convert_time",
                func=lambda args: self.convert_time(**json.loads(args)),
                coroutine=lambda args: self.convert_time(**json.loads(args)),
                description=(
                    "Convert time between timezones. Input should be a JSON string with: "
                    "{'source_timezone': 'America/New_York', 'time': '14:30', 'target_timezone': 'Asia/Tokyo'}"
                )
            )
        ]