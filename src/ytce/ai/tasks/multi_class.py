"""
Multi-class classification task executor.
"""
from typing import Dict, List, Optional

from ytce.ai.domain.comment import Comment
from ytce.ai.domain.config import RunConfig
from ytce.ai.domain.result import TaskResult
from ytce.ai.domain.task import TaskConfig
from ytce.ai.models.base import ModelAdapter
from ytce.ai.tasks.base import execute_task_base


def execute_task(
    task: TaskConfig,
    comments: List[Comment],
    model: ModelAdapter,
    run_config: RunConfig,
    custom_prompt: Optional[str] = None,
) -> Dict[str, TaskResult]:
    """
    Execute multi-class classification task.
    
    Args:
        task: TaskConfig with type=MULTI_CLASS
        comments: List of comments to classify
        model: ModelAdapter for LLM calls
        run_config: Runtime configuration
        custom_prompt: Optional custom context
        
    Returns:
        Tuple of (Dictionary mapping comment_id to TaskResult, TokenUsage)
        
    Raises:
        ValueError: If task type is not MULTI_CLASS
        TaskExecutionError: If execution fails
    """
    if task.type.value != "multi_class":
        raise ValueError(
            f"Task type mismatch: expected multi_class, got {task.type.value}"
        )
    
    results, token_usage = execute_task_base(
        task=task,
        comments=comments,
        model=model,
        run_config=run_config,
        custom_prompt=custom_prompt,
    )
    return results, token_usage


__all__ = ["execute_task"]

