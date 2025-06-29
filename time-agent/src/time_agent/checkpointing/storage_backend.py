"""Abstract storage backend for checkpointing."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StorageBackend(ABC):
    """Abstract base class for checkpoint storage."""
    
    @abstractmethod
    async def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Save a checkpoint.
        
        Args:
            thread_id: Thread/conversation ID
            checkpoint_id: Checkpoint ID
            data: Checkpoint data
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def load_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load a checkpoint.
        
        Args:
            thread_id: Thread/conversation ID
            checkpoint_id: Optional specific checkpoint ID
            
        Returns:
            Checkpoint data or None
        """
        pass
    
    @abstractmethod
    async def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List checkpoints for a thread.
        
        Args:
            thread_id: Thread/conversation ID
            limit: Maximum number to return
            
        Returns:
            List of checkpoint metadata
        """
        pass
    
    @abstractmethod
    async def delete_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> bool:
        """Delete a checkpoint.
        
        Args:
            thread_id: Thread/conversation ID
            checkpoint_id: Checkpoint ID
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def cleanup_old_checkpoints(
        self,
        thread_id: str,
        keep_count: int = 5
    ) -> int:
        """Clean up old checkpoints.
        
        Args:
            thread_id: Thread/conversation ID
            keep_count: Number of recent checkpoints to keep
            
        Returns:
            Number of checkpoints deleted
        """
        pass