"""Synchronizes state between A2A tasks and LangGraph checkpoints."""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from ..protocol.models import A2ATask, TaskStatus
from ..protocol.task_manager import TaskManager
from .a2a_checkpointer import A2ACheckpointer


logger = logging.getLogger(__name__)


class StateSynchronizer:
    """Synchronizes A2A task state with LangGraph checkpoints."""
    
    def __init__(self,
                 task_manager: TaskManager,
                 checkpointer: A2ACheckpointer,
                 auto_checkpoint: bool = True):
        """Initialize state synchronizer.
        
        Args:
            task_manager: A2A task manager
            checkpointer: A2A checkpointer
            auto_checkpoint: Enable automatic checkpointing
        """
        self.task_manager = task_manager
        self.checkpointer = checkpointer
        self.auto_checkpoint = auto_checkpoint
        self._sync_callbacks: Dict[str, Callable] = {}
        
    async def sync_task_to_checkpoint(self, task_id: str) -> Optional[str]:
        """Sync A2A task state to a checkpoint.
        
        Args:
            task_id: Task ID to sync
            
        Returns:
            Checkpoint ID if created
        """
        try:
            # Get task
            task = await self.task_manager.get_task(task_id)
            
            # Prepare checkpoint data
            checkpoint_data = {
                "task_state": task.model_dump(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Create config for checkpointer
            config = {
                "configurable": {
                    "thread_id": f"task:{task_id}"
                }
            }
            
            # Save checkpoint
            updated_config = await self.checkpointer.aput(
                config=config,
                checkpoint={"v": 1, "data": checkpoint_data},
                metadata={
                    "step": 1,
                    "source": "task_sync",
                    "task_status": task.status.value
                }
            )
            
            checkpoint_id = updated_config["configurable"].get("checkpoint_id")
            logger.info(f"Synced task {task_id} to checkpoint {checkpoint_id}")
            
            # Trigger callback if registered
            if task_id in self._sync_callbacks:
                await self._sync_callbacks[task_id](task, checkpoint_id)
                
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Failed to sync task {task_id}: {e}")
            return None
            
    async def restore_task_from_checkpoint(self,
                                         task_id: str,
                                         checkpoint_id: Optional[str] = None) -> bool:
        """Restore A2A task state from checkpoint.
        
        Args:
            task_id: Task ID to restore
            checkpoint_id: Specific checkpoint to restore from
            
        Returns:
            True if restored successfully
        """
        try:
            # Prepare config
            config = {
                "configurable": {
                    "thread_id": f"task:{task_id}"
                }
            }
            
            if checkpoint_id:
                config["configurable"]["checkpoint_id"] = checkpoint_id
                
            # Get checkpoint
            checkpoint_tuple = await self.checkpointer.aget_tuple(config)
            if not checkpoint_tuple:
                logger.warning(f"No checkpoint found for task {task_id}")
                return False
                
            # Extract task state
            checkpoint_data = checkpoint_tuple.checkpoint.get("data", {})
            task_state = checkpoint_data.get("task_state")
            
            if not task_state:
                logger.warning(f"No task state in checkpoint for task {task_id}")
                return False
                
            # Restore task
            task = A2ATask(**task_state)
            self.task_manager.tasks[task_id] = task
            
            logger.info(f"Restored task {task_id} from checkpoint")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore task {task_id}: {e}")
            return False
            
    async def setup_auto_sync(self, task_id: str, interval: int = 30) -> asyncio.Task:
        """Setup automatic synchronization for a task.
        
        Args:
            task_id: Task ID to auto-sync
            interval: Sync interval in seconds
            
        Returns:
            Background sync task
        """
        async def auto_sync_loop():
            """Auto sync loop."""
            while True:
                try:
                    await asyncio.sleep(interval)
                    
                    # Check if task still exists
                    try:
                        task = await self.task_manager.get_task(task_id)
                    except:
                        logger.info(f"Task {task_id} no longer exists, stopping auto-sync")
                        break
                        
                    # Don't sync terminal states repeatedly
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        logger.info(f"Task {task_id} in terminal state, stopping auto-sync")
                        break
                        
                    # Sync state
                    await self.sync_task_to_checkpoint(task_id)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto-sync error for task {task_id}: {e}")
                    
        # Create and return the task
        return asyncio.create_task(auto_sync_loop())
        
    def register_sync_callback(self, task_id: str, callback: Callable) -> None:
        """Register callback for sync events.
        
        Args:
            task_id: Task ID
            callback: Async callback function(task, checkpoint_id)
        """
        self._sync_callbacks[task_id] = callback
        
    async def get_task_checkpoints(self, task_id: str, limit: int = 10) -> list[Dict[str, Any]]:
        """Get checkpoints for a task.
        
        Args:
            task_id: Task ID
            limit: Maximum checkpoints to return
            
        Returns:
            List of checkpoint metadata
        """
        config = {
            "configurable": {
                "thread_id": f"task:{task_id}"
            }
        }
        
        checkpoints = await self.checkpointer.alist(config=config, limit=limit)
        
        # Extract metadata
        result = []
        for cp_tuple in checkpoints:
            metadata = cp_tuple.metadata
            checkpoint_data = cp_tuple.checkpoint.get("data", {})
            
            result.append({
                "created_at": checkpoint_data.get("timestamp"),
                "task_status": metadata.get("task_status"),
                "step": metadata.get("step"),
                "source": metadata.get("source")
            })
            
        return result