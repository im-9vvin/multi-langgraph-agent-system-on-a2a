"""Checkpointing subsystem for persistent state management."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple, CheckpointMetadata, ChannelVersions
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from ..common.exceptions import OrchestratorError
from ..common.logging import get_logger

logger = get_logger(__name__)


class SQLiteCheckpointSaver(BaseCheckpointSaver):
    """SQLite-based checkpoint saver for persistent state storage."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize SQLite checkpoint saver.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default.
        """
        if db_path is None:
            # Default to data directory
            data_dir = Path.home() / ".orchestrator-agent" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "checkpoints.db")
            
        self.db_path = db_path
        self.serializer = JsonPlusSerializer()
        self._init_db()
        
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    parent_id TEXT,
                    checkpoint_data TEXT NOT NULL,
                    metadata TEXT,
                    channel_versions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (thread_id, checkpoint_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thread_created 
                ON checkpoints(thread_id, created_at DESC)
            """)
            conn.commit()
    
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Get a checkpoint tuple.
        
        Args:
            config: Configuration with thread_id and optional checkpoint_id
            
        Returns:
            CheckpointTuple if found, None otherwise
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if not thread_id:
            return None
            
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if checkpoint_id:
                # Get specific checkpoint
                row = conn.execute(
                    """
                    SELECT * FROM checkpoints 
                    WHERE thread_id = ? AND checkpoint_id = ?
                    """,
                    (thread_id, checkpoint_id)
                ).fetchone()
            else:
                # Get latest checkpoint
                row = conn.execute(
                    """
                    SELECT * FROM checkpoints 
                    WHERE thread_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                    """,
                    (thread_id,)
                ).fetchone()
                
            if row:
                checkpoint = Checkpoint(**self.serializer.loads(row["checkpoint_data"]))
                metadata = CheckpointMetadata(
                    **(self.serializer.loads(row["metadata"]) if row["metadata"] else {})
                )
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": row["parent_id"]
                    }
                } if row["parent_id"] else None
                
                return CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parent_config
                )
                
        return None
    
    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Get a checkpoint tuple asynchronously.
        
        Args:
            config: Configuration with thread_id and optional checkpoint_id
            
        Returns:
            CheckpointTuple if found, None otherwise
        """
        # For SQLite, we can just call the sync version since SQLite doesn't support async
        return self.get_tuple(config)
    
    def put(self, config: Dict[str, Any], checkpoint: Checkpoint, 
            metadata: CheckpointMetadata, new_versions: ChannelVersions) -> Dict[str, Any]:
        """Save a checkpoint.
        
        Args:
            config: Configuration with thread_id
            checkpoint: Checkpoint to save
            metadata: Checkpoint metadata
            new_versions: Channel versions for the checkpoint
            
        Returns:
            Updated config with checkpoint_id
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise ValueError("thread_id is required in config")
            
        checkpoint_id = checkpoint.get("id", str(datetime.now().timestamp()))
        parent_id = config.get("configurable", {}).get("checkpoint_id")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints 
                (thread_id, checkpoint_id, parent_id, checkpoint_data, metadata, channel_versions)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    checkpoint_id,
                    parent_id,
                    self.serializer.dumps(checkpoint),
                    self.serializer.dumps(dict(metadata)) if metadata else None,
                    self.serializer.dumps(dict(new_versions)) if new_versions else None
                )
            )
            conn.commit()
            
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            }
        }
    
    async def aput(self, config: Dict[str, Any], checkpoint: Checkpoint,
                   metadata: CheckpointMetadata, new_versions: ChannelVersions) -> Dict[str, Any]:
        """Save a checkpoint asynchronously.
        
        Args:
            config: Configuration with thread_id
            checkpoint: Checkpoint to save
            metadata: Checkpoint metadata
            new_versions: Channel versions for the checkpoint
            
        Returns:
            Updated config with checkpoint_id
        """
        # For SQLite, we can just call the sync version since SQLite doesn't support async
        return self.put(config, checkpoint, metadata, new_versions)
    
    def list(self, config: Optional[Dict[str, Any]] = None,
             *, filter: Optional[Dict[str, Any]] = None,
             before: Optional[Dict[str, Any]] = None,
             limit: Optional[int] = None) -> List[CheckpointTuple]:
        """List checkpoints.
        
        Args:
            config: Optional config to filter by thread_id
            filter: Additional filters (not implemented)
            before: List checkpoints before this config
            limit: Maximum number of checkpoints to return
            
        Returns:
            List of checkpoint tuples
        """
        query = "SELECT * FROM checkpoints"
        params = []
        conditions = []
        
        if config and config.get("configurable", {}).get("thread_id"):
            conditions.append("thread_id = ?")
            params.append(config["configurable"]["thread_id"])
            
        if before and before.get("configurable", {}).get("checkpoint_id"):
            # Get timestamp of before checkpoint
            with sqlite3.connect(self.db_path) as conn:
                before_time = conn.execute(
                    "SELECT created_at FROM checkpoints WHERE checkpoint_id = ?",
                    (before["configurable"]["checkpoint_id"],)
                ).fetchone()
                if before_time:
                    conditions.append("created_at < ?")
                    params.append(before_time[0])
                    
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
            
        checkpoints = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            for row in conn.execute(query, params):
                config = {
                    "configurable": {
                        "thread_id": row["thread_id"],
                        "checkpoint_id": row["checkpoint_id"]
                    }
                }
                checkpoint = Checkpoint(**self.serializer.loads(row["checkpoint_data"]))
                metadata = CheckpointMetadata(
                    **(self.serializer.loads(row["metadata"]) if row["metadata"] else {})
                )
                parent_config = {
                    "configurable": {
                        "thread_id": row["thread_id"],
                        "checkpoint_id": row["parent_id"]
                    }
                } if row["parent_id"] else None
                
                checkpoints.append(CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parent_config
                ))
                
        return checkpoints
    
    async def alist(self, config: Optional[Dict[str, Any]] = None,
                    *, filter: Optional[Dict[str, Any]] = None,
                    before: Optional[Dict[str, Any]] = None,
                    limit: Optional[int] = None) -> List[CheckpointTuple]:
        """List checkpoints asynchronously.
        
        Args:
            config: Optional config to filter by thread_id
            filter: Additional filters (not implemented)
            before: List checkpoints before this config
            limit: Maximum number of checkpoints to return
            
        Returns:
            List of checkpoint tuples
        """
        # For SQLite, we can just call the sync version since SQLite doesn't support async
        return self.list(config, filter=filter, before=before, limit=limit)
    
    async def aput_writes(self, config: Dict[str, Any], writes: Sequence[Tuple[str, Any]], 
                         task_id: str, task_path: str = "") -> None:
        """Save writes asynchronously.
        
        Args:
            config: Configuration
            writes: Sequence of (channel, value) tuples
            task_id: Task ID
            task_path: Task path
        """
        # For SQLite, we don't need to implement this - it's used for streaming writes
        # LangGraph will use aput for the main checkpoint storage
        pass


class CheckpointManager:
    """Manages checkpointing for the orchestrator agent."""
    
    def __init__(self, checkpoint_dir: Optional[str] = None):
        """Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory for checkpoint storage
        """
        self.checkpoint_dir = checkpoint_dir or self._get_default_checkpoint_dir()
        self.saver = SQLiteCheckpointSaver(
            os.path.join(self.checkpoint_dir, "checkpoints.db")
        )
        logger.info(f"Initialized checkpoint manager with dir: {self.checkpoint_dir}")
        
    def _get_default_checkpoint_dir(self) -> str:
        """Get default checkpoint directory."""
        data_dir = Path.home() / ".orchestrator-agent" / "checkpoints"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)
        
    def get_saver(self) -> BaseCheckpointSaver:
        """Get the checkpoint saver instance.
        
        Returns:
            Checkpoint saver for use with LangGraph
        """
        return self.saver
        
    def cleanup_old_checkpoints(self, days: int = 7):
        """Clean up old checkpoints.
        
        Args:
            days: Delete checkpoints older than this many days
        """
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        with sqlite3.connect(self.saver.db_path) as conn:
            deleted = conn.execute(
                """
                DELETE FROM checkpoints 
                WHERE created_at < datetime(?, 'unixepoch')
                """,
                (cutoff_date,)
            ).rowcount
            conn.commit()
            
        logger.info(f"Cleaned up {deleted} old checkpoints")
        
    def export_thread_history(self, thread_id: str, 
                            export_path: Optional[str] = None) -> str:
        """Export conversation history for a thread.
        
        Args:
            thread_id: Thread ID to export
            export_path: Optional path to export to
            
        Returns:
            Path to exported file
        """
        if not export_path:
            export_dir = Path(self.checkpoint_dir) / "exports"
            export_dir.mkdir(exist_ok=True)
            export_path = str(export_dir / f"{thread_id}_{datetime.now().isoformat()}.json")
            
        checkpoints = self.saver.list({"configurable": {"thread_id": thread_id}})
        
        history = {
            "thread_id": thread_id,
            "exported_at": datetime.now().isoformat(),
            "checkpoints": []
        }
        
        for cp_tuple in checkpoints:
            history["checkpoints"].append({
                "checkpoint_id": cp_tuple.config["configurable"]["checkpoint_id"],
                "checkpoint": cp_tuple.checkpoint,
                "metadata": dict(cp_tuple.metadata) if cp_tuple.metadata else {}
            })
            
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Exported thread history to: {export_path}")
        return export_path