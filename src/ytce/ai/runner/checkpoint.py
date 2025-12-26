"""
Checkpoint management for resumable AI analysis.

This module provides functionality to save and restore analysis progress,
allowing runs to be interrupted and resumed.
"""
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Set

logger = logging.getLogger("ytce.ai.checkpoint")


@dataclass
class Checkpoint:
    """Represents analysis progress checkpoint."""
    video_id: str
    total_comments: int
    total_tasks: int
    task_ids: List[str]
    # Map of task_id -> set of completed comment_ids
    completed: Dict[str, List[str]]
    run_id: Optional[str] = None
    # Debug tracking fields
    created_at: Optional[str] = None
    last_updated_at: Optional[str] = None
    batches_completed: int = 0
    total_batches_processed: int = 0
    current_task: Optional[str] = None
    current_batch: int = 0
    total_batches: int = 0
    
    def is_comment_task_done(self, comment_id: str, task_id: str) -> bool:
        """Check if a specific comment-task combination is completed."""
        return comment_id in self.completed.get(task_id, [])
    
    def mark_task_batch_complete(self, task_id: str, comment_ids: List[str], batch_num: int = 0, total_batches: int = 0) -> None:
        """Mark a batch of comments as completed for a task."""
        if task_id not in self.completed:
            self.completed[task_id] = []
        self.completed[task_id].extend(comment_ids)
        # Remove duplicates while preserving order
        self.completed[task_id] = list(dict.fromkeys(self.completed[task_id]))
        
        # Update debug tracking
        self.last_updated_at = datetime.now().isoformat()
        self.batches_completed += 1
        self.total_batches_processed += 1
        self.current_task = task_id
        self.current_batch = batch_num
        self.total_batches = total_batches
        
        logger.debug(
            f"Checkpoint updated: task={task_id}, batch={batch_num}/{total_batches}, "
            f"comments={len(comment_ids)}, total_completed={len(self.completed[task_id])}"
        )
    
    def get_pending_comments(self, task_id: str, all_comment_ids: List[str]) -> List[str]:
        """Get list of comment IDs that haven't been processed for a task."""
        completed_ids = set(self.completed.get(task_id, []))
        return [cid for cid in all_comment_ids if cid not in completed_ids]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        """Create checkpoint from dictionary."""
        return cls(**data)


def get_checkpoint_path(results_dir: str) -> str:
    """Get the checkpoint file path for a results directory."""
    return os.path.join(results_dir, ".checkpoint.json")


def load_checkpoint(results_dir: str) -> Optional[Checkpoint]:
    """
    Load checkpoint from results directory.
    
    Args:
        results_dir: Directory where results are saved
        
    Returns:
        Checkpoint object if found, None otherwise
    """
    checkpoint_path = get_checkpoint_path(results_dir)
    if not os.path.exists(checkpoint_path):
        return None
    
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        checkpoint = Checkpoint.from_dict(data)
        total_completed = sum(len(ids) for ids in checkpoint.completed.values())
        logger.info(
            f"Loaded checkpoint: video={checkpoint.video_id}, "
            f"completed_items={total_completed}/{checkpoint.total_comments * checkpoint.total_tasks}, "
            f"batches_processed={checkpoint.total_batches_processed}, "
            f"created_at={checkpoint.created_at}, "
            f"last_updated={checkpoint.last_updated_at}"
        )
        if checkpoint.current_task:
            logger.info(
                f"  Current progress: task={checkpoint.current_task}, "
                f"batch={checkpoint.current_batch}/{checkpoint.total_batches}"
            )
        return checkpoint
    except Exception as e:
        logger.warning(f"Failed to load checkpoint: {e}")
        return None


def save_checkpoint(checkpoint: Checkpoint, results_dir: str) -> None:
    """
    Save checkpoint to results directory.
    
    Args:
        checkpoint: Checkpoint to save
        results_dir: Directory where results are saved
    """
    checkpoint_path = get_checkpoint_path(results_dir)
    os.makedirs(results_dir, exist_ok=True)
    
    try:
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)
        logger.debug(f"Checkpoint saved to: {checkpoint_path}")
    except Exception as e:
        logger.warning(f"Failed to save checkpoint: {e}")


def delete_checkpoint(results_dir: str) -> None:
    """
    Delete checkpoint file from results directory.
    
    Args:
        results_dir: Directory where checkpoint is saved
    """
    checkpoint_path = get_checkpoint_path(results_dir)
    if os.path.exists(checkpoint_path):
        try:
            os.remove(checkpoint_path)
            logger.info("Checkpoint deleted (analysis complete)")
        except Exception as e:
            logger.warning(f"Failed to delete checkpoint: {e}")


def create_checkpoint(
    video_id: str,
    total_comments: int,
    task_ids: List[str],
    run_id: Optional[str] = None,
) -> Checkpoint:
    """
    Create a new checkpoint.
    
    Args:
        video_id: ID of the video being analyzed
        total_comments: Total number of comments
        task_ids: List of task IDs to process
        run_id: Optional run identifier
        
    Returns:
        New Checkpoint object
    """
    now = datetime.now().isoformat()
    checkpoint = Checkpoint(
        video_id=video_id,
        total_comments=total_comments,
        total_tasks=len(task_ids),
        task_ids=task_ids,
        completed={},
        run_id=run_id,
        created_at=now,
        last_updated_at=now,
        batches_completed=0,
        total_batches_processed=0,
        current_task=None,
        current_batch=0,
        total_batches=0,
    )
    logger.info(
        f"Checkpoint created: video={video_id}, comments={total_comments}, "
        f"tasks={len(task_ids)}, created_at={now}"
    )
    return checkpoint


__all__ = [
    "Checkpoint",
    "get_checkpoint_path",
    "load_checkpoint",
    "save_checkpoint",
    "delete_checkpoint",
    "create_checkpoint",
]

