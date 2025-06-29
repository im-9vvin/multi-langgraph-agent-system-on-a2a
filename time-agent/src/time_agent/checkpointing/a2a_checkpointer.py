"""Custom LangGraph checkpointer for A2A integration."""

import json
import logging
from typing import Any, Dict, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint

from .storage_backend import StorageBackend
from .memory_backend import MemoryBackend

logger = logging.getLogger(__name__)


class A2ACheckpointer(BaseCheckpointSaver):
    """LangGraph checkpointer that integrates with A2A protocol."""
    
    def __init__(self, storage: Optional[StorageBackend] = None):
        """Initialize A2A checkpointer.
        
        Args:
            storage: Storage backend (defaults to MemoryBackend)
        """
        super().__init__()
        self.storage = storage or MemoryBackend()
    
    async def aget(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        """Get a checkpoint.
        
        Args:
            config: Configuration with thread_id and optional checkpoint_id
            
        Returns:
            Checkpoint or None
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if not thread_id:
            return None
        
        try:
            data = await self.storage.load_checkpoint(thread_id, checkpoint_id)
            if data:
                return Checkpoint(**data)
            return None
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save a checkpoint.
        
        Args:
            config: Configuration with thread_id
            checkpoint: Checkpoint to save
            metadata: Optional metadata
            
        Returns:
            Updated configuration
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        
        if not thread_id:
            raise ValueError("thread_id is required in config")
        
        # Generate checkpoint ID
        checkpoint_id = checkpoint.get("id", f"cp_{checkpoint.get('ts', 'unknown')}")
        
        try:
            # Prepare checkpoint data
            checkpoint_data = {
                **checkpoint,
                "metadata": metadata or {}
            }
            
            # Save checkpoint
            success = await self.storage.save_checkpoint(
                thread_id,
                checkpoint_id,
                checkpoint_data
            )
            
            if success:
                logger.info(f"Saved checkpoint {checkpoint_id} for thread {thread_id}")
                
                # Return updated config
                return {
                    **config,
                    "configurable": {
                        **config.get("configurable", {}),
                        "checkpoint_id": checkpoint_id
                    }
                }
            else:
                raise RuntimeError("Failed to save checkpoint")
                
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise
    
    async def alist(
        self,
        config: Dict[str, Any],
        limit: int = 10
    ) -> list[tuple[Dict[str, Any], Checkpoint]]:
        """List checkpoints for a thread.
        
        Args:
            config: Configuration with thread_id
            limit: Maximum number to return
            
        Returns:
            List of (config, checkpoint) tuples
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        
        if not thread_id:
            return []
        
        try:
            checkpoints = await self.storage.list_checkpoints(thread_id, limit)
            
            result = []
            for cp_meta in checkpoints:
                cp_config = {
                    **config,
                    "configurable": {
                        **config.get("configurable", {}),
                        "checkpoint_id": cp_meta["id"]
                    }
                }
                
                # Load full checkpoint data
                cp_data = await self.storage.load_checkpoint(
                    thread_id,
                    cp_meta["id"]
                )
                
                if cp_data:
                    result.append((cp_config, Checkpoint(**cp_data)))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []
    
    def get(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        """Sync version of get (not implemented)."""
        raise NotImplementedError("Use aget for async operations")
    
    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sync version of put (not implemented)."""
        raise NotImplementedError("Use aput for async operations")
    
    def list(
        self,
        config: Dict[str, Any],
        limit: int = 10
    ) -> list[tuple[Dict[str, Any], Checkpoint]]:
        """Sync version of list (not implemented)."""
        raise NotImplementedError("Use alist for async operations")