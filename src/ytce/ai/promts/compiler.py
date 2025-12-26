"""
Prompt compiler for AI comment analysis.

This module provides the main interface for compiling TaskConfig and comments
into prompts ready for LLM consumption.
"""
from typing import List, Optional

from ytce.ai.domain.comment import Comment
from ytce.ai.domain.task import TaskConfig
from ytce.ai.promts.templates import build_base_prompt


def compile_prompt(
    task: TaskConfig,
    comments: List[Comment],
    custom_prompt: Optional[str] = None,
    max_comment_length: Optional[int] = None,
) -> str:
    """
    Generate prompt for batch of comments.
    
    This is the main entry point for prompt compilation. It takes a TaskConfig
    and a list of comments, and produces a complete prompt string that can be
    sent to an LLM.
    
    The prompt includes:
    - Task-specific instructions based on TaskType
    - Custom context (if provided)
    - Formatted comment data
    - Strict JSON output format requirements
    
    Args:
        task: TaskConfig describing what analysis to perform
        comments: List of Comment objects to analyze
        custom_prompt: Optional custom context/background information
        
    Returns:
        Complete prompt string ready for LLM
        
    Raises:
        ValueError: If task configuration is invalid
        
    Example:
        >>> from ytce.ai.domain.task import TaskConfig, TaskType
        >>> from ytce.ai.domain.comment import Comment
        >>> 
        >>> task = TaskConfig(
        ...     id="sentiment",
        ...     type=TaskType.BINARY_CLASSIFICATION,
        ...     question="Is this comment positive?",
        ...     labels=["yes", "no"]
        ... )
        >>> 
        >>> comments = [
        ...     Comment(id="c1", text="Great video!"),
        ...     Comment(id="c2", text="Not helpful")
        ... ]
        >>> 
        >>> prompt = compile_prompt(task, comments)
        >>> assert "Great video!" in prompt
        >>> assert "yes" in prompt or "no" in prompt
    """
    if not comments:
        raise ValueError("Cannot compile prompt: comments list is empty")
    
    # Validate that all comments have required fields
    for comment in comments:
        if not comment.id:
            raise ValueError("Comment missing required field: id")
        if not comment.text:
            raise ValueError("Comment missing required field: text")
    
    # Use template builder to construct the prompt
    return build_base_prompt(
        task=task,
        comments=comments,
        custom_prompt=custom_prompt,
        max_comment_length=max_comment_length,
    )


__all__ = [
    "compile_prompt",
]
