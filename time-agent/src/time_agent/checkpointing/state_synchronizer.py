"""State synchronization between A2A tasks and LangGraph checkpoints."""

import logging
from typing import Any, Dict, Optional

from ..protocol.models import A2ATask, TaskStatus
from ..protocol.task_manager import TaskManager
from .a2a_checkpointer import A2ACheckpointer

logger = logging.getLogger(__name__)


class StateSynchronizer:
    """Synchronizes state between A2A tasks and LangGraph checkpoints."""
    
    def __init__(
        self,
        task_manager: TaskManager,
        checkpointer: A2ACheckpointer
    ):
        """Initialize state synchronizer.
        
        Args:
            task_manager: A2A task manager
            checkpointer: LangGraph checkpointer
        """
        self.task_manager = task_manager
        self.checkpointer = checkpointer
        self.auto_checkpoint = False  # Can be enabled if needed
    
    async def sync_task_to_checkpoint(
        self,
        task: A2ATask,
        checkpoint_data: Dict[str, Any]
    ) -> bool:
        """Sync A2A task state to checkpoint.
        
        Args:
            task: A2A task
            checkpoint_data: Checkpoint data to save
            
        Returns:
            Success status
        """
        try:
            # Create config for checkpointer
            config = {
                "configurable": {
                    "thread_id": task.task_id,
                    "task_metadata": {
                        "status": task.status.value,
                        "created_at": task.created_at.isoformat(),
                        "updated_at": task.updated_at.isoformat()
                    }
                }
            }
            
            # Save checkpoint
            await self.checkpointer.aput(
                config,
                checkpoint_data,
                metadata={
                    "task_id": task.task_id,
                    "task_status": task.status.value
                }
            )
            
            logger.info(f"Synced task {task.task_id} to checkpoint")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync task to checkpoint: {e}")
            return False
    
    async def restore_from_checkpoint(
        self,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Restore task state from checkpoint.
        
        Args:
            task_id: Task ID
            
        Returns:
            Restored state or None
        """
        try:
            # Get task
            task = await self.task_manager.get_task(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return None
            
            # Load checkpoint
            config = {
                "configurable": {
                    "thread_id": task_id
                }
            }
            
            checkpoint = await self.checkpointer.aget(config)
            if checkpoint:
                logger.info(f"Restored state for task {task_id}")
                return checkpoint
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to restore from checkpoint: {e}")
            return None
    
    async def mark_checkpoint_on_completion(
        self,
        task_id: str,
        final_state: Dict[str, Any]
    ) -> bool:
        """Mark checkpoint when task completes.
        
        Args:
            task_id: Task ID
            final_state: Final state data
            
        Returns:
            Success status
        """
        try:
            # Update task status
            task = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                output_data=final_state
            )
            
            if not task:
                return False
            
            # Save final checkpoint
            config = {
                "configurable": {
                    "thread_id": task_id,
                    "is_final": True
                }
            }
            
            await self.checkpointer.aput(
                config,
                final_state,
                metadata={
                    "task_id": task_id,
                    "is_final": True,
                    "completed_at": task.updated_at.isoformat()
                }
            )
            
            logger.info(f"Marked final checkpoint for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark checkpoint on completion: {e}")
            return False
    
    async def get_task_checkpoints(
        self,
        task_id: str,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """Get all checkpoints for a task.
        
        Args:
            task_id: Task ID
            limit: Maximum number to return
            
        Returns:
            List of checkpoint metadata
        """
        try:
            config = {
                "configurable": {
                    "thread_id": task_id
                }
            }
            
            checkpoints = await self.checkpointer.alist(config, limit)
            
            return [
                {
                    "checkpoint_id": cp[0]["configurable"].get("checkpoint_id"),
                    "metadata": cp[1].get("metadata", {}),
                    "timestamp": cp[1].get("ts")
                }
                for cp in checkpoints
            ]
            
        except Exception as e:
            logger.error(f"Failed to get task checkpoints: {e}")
            return []