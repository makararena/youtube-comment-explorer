"""
Batch management utilities for comment processing.

This module provides functions to split comments into batches
for efficient LLM processing.
"""
from typing import List, TypeVar

from ytce.ai.domain.comment import Comment

T = TypeVar("T")


def split_into_batches(items: List[T], batch_size: int) -> List[List[T]]:
    """
    Split a list into batches of specified size.
    
    Args:
        items: List of items to batch
        batch_size: Maximum size of each batch
        
    Returns:
        List of batches, where each batch is a list of items
        
    Example:
        >>> split_into_batches([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    if batch_size <= 0:
        raise ValueError(f"batch_size must be positive, got {batch_size}")
    
    if not items:
        return []
    
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i : i + batch_size])
    
    return batches


def batch_comments(comments: List[Comment], batch_size: int) -> List[List[Comment]]:
    """
    Split comments into batches for LLM processing.
    
    This is a convenience wrapper around split_into_batches that
    provides type hints specific to Comment objects.
    
    Args:
        comments: List of comments to batch
        batch_size: Maximum number of comments per batch
        
    Returns:
        List of comment batches
    """
    return split_into_batches(comments, batch_size)


__all__ = [
    "split_into_batches",
    "batch_comments",
]

