"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime


class StorageBackend(ABC):
    """Abstract base class for checkpoint storage backends."""
    
    @abstractmethod
    async def save_checkpoint(self,
                            checkpoint_id: str,
                            task_id: str,
                            state: Dict[str, Any],
                            metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save a checkpoint.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            task_id: Associated task ID
            state: State data to checkpoint
            metadata: Optional metadata
        """
        pass
    
    @abstractmethod
    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Load a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Checkpoint data or None if not found
        """
        pass
    
    @abstractmethod
    async def list_checkpoints(self,
                             task_id: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """List checkpoints.
        
        Args:
            task_id: Optional task ID filter
            limit: Maximum number of results
            
        Returns:
            List of checkpoint metadata
        """
        pass
    
    @abstractmethod
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def get_latest_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest checkpoint for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Latest checkpoint data or None
        """
        pass