"""Custom checkpointer for A2A and LangGraph integration."""

import uuid
import logging
from typing import Any, Dict, Optional, Sequence
from datetime import datetime

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata
from langgraph.checkpoint.base import CheckpointTuple

from .storage_backend import StorageBackend


logger = logging.getLogger(__name__)


class A2ACheckpointer(BaseCheckpointSaver):
    """Custom checkpointer that bridges A2A tasks with LangGraph state."""
    
    def __init__(self, storage_backend: StorageBackend):
        """Initialize A2A checkpointer.
        
        Args:
            storage_backend: Storage backend implementation
        """
        super().__init__()
        self.storage = storage_backend
        
    async def aput(self,
                  config: Dict[str, Any],
                  checkpoint: Checkpoint,
                  metadata: CheckpointMetadata,
                  new_versions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Save a checkpoint.
        
        Args:
            config: Configuration with thread_id
            checkpoint: Checkpoint data
            metadata: Checkpoint metadata
            new_versions: Optional new versions
            
        Returns:
            Updated configuration
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise ValueError("thread_id required in config")
            
        # Extract task_id from thread_id if it contains it
        # Format: "task:{task_id}" or just "{task_id}"
        task_id = thread_id.replace("task:", "") if thread_id.startswith("task:") else thread_id
        
        # Generate checkpoint ID
        checkpoint_id = str(uuid.uuid4())
        
        # Prepare checkpoint data
        checkpoint_data = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "config": config,
            "new_versions": new_versions,
            "thread_id": thread_id
        }
        
        # Save checkpoint
        await self.storage.save_checkpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            state=checkpoint_data,
            metadata={
                "step": metadata.get("step", 0),
                "score": metadata.get("score"),
                "source": metadata.get("source", "a2a_checkpointer")
            }
        )
        
        logger.debug(f"Saved checkpoint {checkpoint_id} for task {task_id}")
        
        # Return updated config with checkpoint info
        return {
            **config,
            "configurable": {
                **config.get("configurable", {}),
                "checkpoint_id": checkpoint_id,
                "checkpoint_ns": "",
            }
        }
        
    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Get a checkpoint tuple.
        
        Args:
            config: Configuration with thread_id and optional checkpoint_id
            
        Returns:
            CheckpointTuple or None
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None
            
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        task_id = thread_id.replace("task:", "") if thread_id.startswith("task:") else thread_id
        
        # Load specific checkpoint or latest
        if checkpoint_id:
            checkpoint_data = await self.storage.load_checkpoint(checkpoint_id)
        else:
            checkpoint_data = await self.storage.get_latest_checkpoint(task_id)
            
        if not checkpoint_data:
            return None
            
        # Extract components
        state_data = checkpoint_data.get("state", {})
        checkpoint = state_data.get("checkpoint")
        metadata = state_data.get("metadata", {})
        parent_config = state_data.get("config", config)
        
        # Create checkpoint tuple
        return CheckpointTuple(
            config=parent_config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=None  # We don't track parent checkpoints in this implementation
        )
        
    async def alist(self,
                   config: Optional[Dict[str, Any]] = None,
                   *,
                   filter: Optional[Dict[str, Any]] = None,
                   before: Optional[Dict[str, Any]] = None,
                   limit: Optional[int] = None) -> Sequence[CheckpointTuple]:
        """List checkpoints.
        
        Args:
            config: Optional configuration filter
            filter: Optional metadata filter
            before: Optional timestamp filter
            limit: Maximum results
            
        Returns:
            List of checkpoint tuples
        """
        # Extract task_id from config if provided
        task_id = None
        if config and "configurable" in config:
            thread_id = config["configurable"].get("thread_id")
            if thread_id:
                task_id = thread_id.replace("task:", "") if thread_id.startswith("task:") else thread_id
                
        # List checkpoints
        checkpoints = await self.storage.list_checkpoints(
            task_id=task_id,
            limit=limit or 100
        )
        
        # Convert to checkpoint tuples
        tuples = []
        for cp_meta in checkpoints:
            # Load full checkpoint data
            checkpoint_data = await self.storage.load_checkpoint(cp_meta["checkpoint_id"])
            if checkpoint_data:
                state_data = checkpoint_data.get("state", {})
                tuples.append(
                    CheckpointTuple(
                        config=state_data.get("config", {}),
                        checkpoint=state_data.get("checkpoint"),
                        metadata=state_data.get("metadata", {}),
                        parent_config=None
                    )
                )
                
        return tuples
        
    def put(self,
           config: Dict[str, Any],
           checkpoint: Checkpoint,
           metadata: CheckpointMetadata,
           new_versions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sync version of put (not implemented)."""
        raise NotImplementedError("Use async aput method")
        
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Sync version of get_tuple (not implemented)."""
        raise NotImplementedError("Use async aget_tuple method")
        
    def list(self,
            config: Optional[Dict[str, Any]] = None,
            *,
            filter: Optional[Dict[str, Any]] = None,
            before: Optional[Dict[str, Any]] = None,
            limit: Optional[int] = None) -> Sequence[CheckpointTuple]:
        """Sync version of list (not implemented)."""
        raise NotImplementedError("Use async alist method")