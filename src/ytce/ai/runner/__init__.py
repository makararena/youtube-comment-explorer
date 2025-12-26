"""
Runner layer for AI comment analysis.

This module orchestrates the entire analysis pipeline, coordinating
between input loading, task execution, and result aggregation.
"""
from ytce.ai.runner.analysis import run_analysis
from ytce.ai.runner.batching import batch_comments, split_into_batches

__all__ = [
    "run_analysis",
    "batch_comments",
    "split_into_batches",
]

