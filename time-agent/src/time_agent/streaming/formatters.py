"""SSE formatting utilities."""

import json
from typing import Any, Dict, Optional


class SSEFormatter:
    """Formats data for Server-Sent Events."""
    
    @staticmethod
    def format_event(
        data: Any,
        event: Optional[str] = None,
        id: Optional[str] = None,
        retry: Optional[int] = None
    ) -> str:
        """Format data as SSE event.
        
        Args:
            data: Event data
            event: Optional event type
            id: Optional event ID
            retry: Optional retry interval in milliseconds
            
        Returns:
            SSE-formatted string
        """
        lines = []
        
        if id:
            lines.append(f"id: {id}")
        
        if event:
            lines.append(f"event: {event}")
        
        if retry is not None:
            lines.append(f"retry: {retry}")
        
        # Format data
        if isinstance(data, str):
            lines.append(f"data: {data}")
        else:
            # JSON serialize non-string data
            lines.append(f"data: {json.dumps(data)}")
        
        # SSE requires double newline at end
        return "\n".join(lines) + "\n\n"
    
    @staticmethod
    def format_comment(comment: str) -> str:
        """Format a comment (keep-alive).
        
        Args:
            comment: Comment text
            
        Returns:
            SSE comment string
        """
        return f": {comment}\n\n"
    
    @staticmethod
    def format_task_event(
        task_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> str:
        """Format a task-specific event.
        
        Args:
            task_id: Task ID
            event_type: Event type
            data: Event data
            
        Returns:
            SSE-formatted string
        """
        event_data = {
            "task_id": task_id,
            "type": event_type,
            "data": data
        }
        
        return SSEFormatter.format_event(
            data=event_data,
            event="task_update",
            id=task_id
        )