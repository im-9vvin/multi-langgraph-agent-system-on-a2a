"""In-memory storage backend implementation."""

import asyncio
from typing import Any, Dict, Optional, List
from datetime import datetime
from collections import defaultdict

from .storage_backend import StorageBackend


class MemoryBackend(StorageBackend):
    """In-memory checkpoint storage backend."""
    
    def __init__(self):
        """Initialize memory backend."""
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._task_checkpoints: Dict[str, List[str]] = defaultdict(list)
        self._lock = asyncio.Lock()
        
    async def save_checkpoint(self,
                            checkpoint_id: str,
                            task_id: str,
                            state: Dict[str, Any],
                            metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save a checkpoint to memory.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            task_id: Associated task ID
            state: State data to checkpoint
            metadata: Optional metadata
        """
        async with self._lock:
            checkpoint = {
                'checkpoint_id': checkpoint_id,
                'task_id': task_id,
                'state': state,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            self._checkpoints[checkpoint_id] = checkpoint
            
            # Track by task ID
            if checkpoint_id not in self._task_checkpoints[task_id]:
                self._task_checkpoints[task_id].append(checkpoint_id)
                
    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Load a checkpoint from memory.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Checkpoint data or None if not found
        """
        return self._checkpoints.get(checkpoint_id)
        
    async def list_checkpoints(self,
                             task_id: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """List checkpoints from memory.
        
        Args:
            task_id: Optional task ID filter
            limit: Maximum number of results
            
        Returns:
            List of checkpoint metadata
        """
        checkpoints = []
        
        if task_id:
            # Get checkpoints for specific task
            for checkpoint_id in self._task_checkpoints.get(task_id, []):
                if checkpoint_id in self._checkpoints:
                    checkpoint = self._checkpoints[checkpoint_id].copy()
                    # Return metadata only
                    checkpoints.append({
                        'checkpoint_id': checkpoint['checkpoint_id'],
                        'task_id': checkpoint['task_id'],
                        'created_at': checkpoint['created_at'],
                        'metadata': checkpoint['metadata']
                    })
        else:
            # Get all checkpoints
            for checkpoint in self._checkpoints.values():
                checkpoints.append({
                    'checkpoint_id': checkpoint['checkpoint_id'],
                    'task_id': checkpoint['task_id'],
                    'created_at': checkpoint['created_at'],
                    'metadata': checkpoint['metadata']
                })
                
        # Sort by creation time, newest first
        checkpoints.sort(key=lambda x: x['created_at'], reverse=True)
        
        return checkpoints[:limit]
        
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint from memory.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if checkpoint_id not in self._checkpoints:
                return False
                
            checkpoint = self._checkpoints[checkpoint_id]
            task_id = checkpoint['task_id']
            
            # Remove from checkpoints
            del self._checkpoints[checkpoint_id]
            
            # Remove from task tracking
            if task_id in self._task_checkpoints:
                self._task_checkpoints[task_id].remove(checkpoint_id)
                if not self._task_checkpoints[task_id]:
                    del self._task_checkpoints[task_id]
                    
            return True
            
    async def get_latest_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest checkpoint for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Latest checkpoint data or None
        """
        checkpoint_ids = self._task_checkpoints.get(task_id, [])
        if not checkpoint_ids:
            return None
            
        # Get all checkpoints for the task
        checkpoints = []
        for checkpoint_id in checkpoint_ids:
            if checkpoint_id in self._checkpoints:
                checkpoints.append(self._checkpoints[checkpoint_id])
                
        if not checkpoints:
            return None
            
        # Sort by creation time and return the latest
        checkpoints.sort(key=lambda x: x['created_at'], reverse=True)
        return checkpoints[0]