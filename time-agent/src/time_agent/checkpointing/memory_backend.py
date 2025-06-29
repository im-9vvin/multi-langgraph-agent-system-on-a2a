"""In-memory storage backend for checkpointing."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from .storage_backend import StorageBackend


class MemoryBackend(StorageBackend):
    """In-memory implementation of checkpoint storage."""
    
    def __init__(self):
        """Initialize memory backend."""
        self._storage: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self._lock = asyncio.Lock()
    
    async def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Save a checkpoint to memory.
        
        Args:
            thread_id: Thread/conversation ID
            checkpoint_id: Checkpoint ID
            data: Checkpoint data
            
        Returns:
            Success status
        """
        async with self._lock:
            checkpoint = {
                "id": checkpoint_id,
                "thread_id": thread_id,
                "data": data,
                "created_at": datetime.utcnow().isoformat(),
                "version": 1
            }
            
            # Update version if checkpoint exists
            if checkpoint_id in self._storage[thread_id]:
                checkpoint["version"] = self._storage[thread_id][checkpoint_id].get("version", 0) + 1
            
            self._storage[thread_id][checkpoint_id] = checkpoint
            return True
    
    async def load_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load a checkpoint from memory.
        
        Args:
            thread_id: Thread/conversation ID
            checkpoint_id: Optional specific checkpoint ID
            
        Returns:
            Checkpoint data or None
        """
        async with self._lock:
            thread_checkpoints = self._storage.get(thread_id, {})
            
            if not thread_checkpoints:
                return None
            
            if checkpoint_id:
                # Load specific checkpoint
                checkpoint = thread_checkpoints.get(checkpoint_id)
                return checkpoint["data"] if checkpoint else None
            else:
                # Load latest checkpoint
                if thread_checkpoints:
                    latest = max(
                        thread_checkpoints.values(),
                        key=lambda x: x["created_at"]
                    )
                    return latest["data"]
                return None
    
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
        async with self._lock:
            thread_checkpoints = self._storage.get(thread_id, {})
            
            # Sort by creation time (newest first)
            checkpoints = sorted(
                thread_checkpoints.values(),
                key=lambda x: x["created_at"],
                reverse=True
            )
            
            # Return metadata only
            return [
                {
                    "id": cp["id"],
                    "thread_id": cp["thread_id"],
                    "created_at": cp["created_at"],
                    "version": cp["version"]
                }
                for cp in checkpoints[:limit]
            ]
    
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
        async with self._lock:
            if thread_id in self._storage and checkpoint_id in self._storage[thread_id]:
                del self._storage[thread_id][checkpoint_id]
                
                # Clean up empty thread entries
                if not self._storage[thread_id]:
                    del self._storage[thread_id]
                
                return True
            return False
    
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
        async with self._lock:
            thread_checkpoints = self._storage.get(thread_id, {})
            
            if len(thread_checkpoints) <= keep_count:
                return 0
            
            # Sort by creation time
            sorted_checkpoints = sorted(
                thread_checkpoints.items(),
                key=lambda x: x[1]["created_at"],
                reverse=True
            )
            
            # Delete old checkpoints
            deleted = 0
            for checkpoint_id, _ in sorted_checkpoints[keep_count:]:
                del self._storage[thread_id][checkpoint_id]
                deleted += 1
            
            return deleted
    
    async def clear_all(self):
        """Clear all checkpoints (for testing)."""
        async with self._lock:
            self._storage.clear()