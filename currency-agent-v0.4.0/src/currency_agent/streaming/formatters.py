"""SSE formatting utilities."""

import json
from typing import Any, Optional, Dict


class SSEFormatter:
    """Formats data for Server-Sent Events transmission."""
    
    @staticmethod
    def format_event(data: Any,
                    event: Optional[str] = None,
                    id: Optional[str] = None,
                    retry: Optional[int] = None) -> str:
        """Format data as SSE event.
        
        Args:
            data: Event data (will be JSON serialized)
            event: Event type
            id: Event ID
            retry: Retry time in milliseconds
            
        Returns:
            SSE formatted string
        """
        lines = []
        
        # Add event type
        if event:
            lines.append(f"event: {event}")
            
        # Add event ID
        if id:
            lines.append(f"id: {id}")
            
        # Add retry time
        if retry is not None:
            lines.append(f"retry: {retry}")
            
        # Add data
        if data is not None:
            # Serialize data to JSON
            if isinstance(data, str):
                json_data = data
            else:
                json_data = json.dumps(data, ensure_ascii=False)
                
            # Split data by newlines for proper SSE formatting
            for line in json_data.split('\n'):
                lines.append(f"data: {line}")
                
        # Add empty line to signal end of event
        lines.append('')
        
        return '\n'.join(lines) + '\n'
    
    @staticmethod
    def format_comment(comment: str) -> str:
        """Format a comment (used for keepalive).
        
        Args:
            comment: Comment text
            
        Returns:
            SSE formatted comment
        """
        return f": {comment}\n\n"
    
    @staticmethod
    def format_retry(retry_ms: int) -> str:
        """Format retry directive.
        
        Args:
            retry_ms: Retry time in milliseconds
            
        Returns:
            SSE formatted retry directive
        """
        return f"retry: {retry_ms}\n\n"
    
    @staticmethod
    def parse_event(sse_data: str) -> Dict[str, Any]:
        """Parse SSE formatted data back to components.
        
        Args:
            sse_data: SSE formatted string
            
        Returns:
            Dictionary with event components
        """
        result = {
            'event': None,
            'id': None,
            'retry': None,
            'data': []
        }
        
        lines = sse_data.strip().split('\n')
        
        for line in lines:
            if not line:
                continue
                
            if line.startswith(':'):
                # Comment, skip
                continue
                
            if ':' not in line:
                continue
                
            field, value = line.split(':', 1)
            value = value.lstrip()
            
            if field == 'event':
                result['event'] = value
            elif field == 'id':
                result['id'] = value
            elif field == 'retry':
                try:
                    result['retry'] = int(value)
                except ValueError:
                    pass
            elif field == 'data':
                result['data'].append(value)
                
        # Join data lines
        if result['data']:
            data_str = '\n'.join(result['data'])
            try:
                result['data'] = json.loads(data_str)
            except json.JSONDecodeError:
                result['data'] = data_str
        else:
            result['data'] = None
            
        return result