"""
Main analysis orchestration logic.

This module provides the core run_analysis() function that orchestrates
the entire AI analysis pipeline.
"""
import logging
import os
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

from ytce.ai.domain.comment import Comment
from ytce.ai.domain.config import RunConfig
from ytce.ai.domain.result import AnalysisResult, EnrichedComment, TaskResult
from ytce.ai.domain.task import TaskConfig
from ytce.ai.input.comments import load_comments_from_config
from ytce.ai.input.job import JobSpec
from ytce.ai.models.base import ModelAdapter
from ytce.ai.models import create_adapter
from ytce.ai.models.tokens import TokenUsage, aggregate_costs
from ytce.ai.runner.batching import batch_comments
from ytce.ai.runner.checkpoint import (
    Checkpoint,
    load_checkpoint,
    save_checkpoint,
    delete_checkpoint,
    create_checkpoint,
)
from ytce.ai.tasks import execute_task
from ytce.ai.tasks.base import TaskExecutionError

if TYPE_CHECKING:
    from ytce.ai.models.tokens import CostSummary

logger = logging.getLogger("ytce.ai.runner")


def run_analysis(
    job: JobSpec,
    run_config: RunConfig,
    progress_callback: Optional[Callable[[int, int, str, bool], None]] = None,
    is_preview: bool = False,
    checkpoint_dir: Optional[str] = None,
    enable_checkpoint: bool = True,
) -> tuple[AnalysisResult, "CostSummary"]:
    """
    Main entry point for AI analysis.
    
    Orchestrates the entire analysis pipeline:
    1. Load comments using job.input configuration
    2. Create model adapter from run_config
    3. For each task in job.tasks:
       - Split comments into batches
       - Execute task on each batch
       - Collect TaskResults
    4. Merge results into EnrichedComment objects
    5. Return AnalysisResult
    
    Args:
        job: JobSpec containing input config, tasks, and custom prompt
        run_config: Runtime configuration (model, API key, batch size, etc.)
        
    Returns:
        AnalysisResult containing all enriched comments
        
    Raises:
        FileNotFoundError: If comment file doesn't exist
        TaskExecutionError: If task execution fails
        ValueError: If configuration is invalid
        
    Example:
        >>> from ytce.ai.input.job import load_job
        >>> from ytce.ai.domain.config import RunConfig
        >>> 
        >>> job = load_job("questions.yaml")
        >>> run_config = RunConfig(
        ...     model="gpt-4.1-nano",
        ...     api_key="sk-...",
        ...     batch_size=20
        ... )
        >>> 
        >>> result = run_analysis(job, run_config)
        >>> print(f"Analyzed {len(result.enriched_comments)} comments")
    """
    # Step 1: Load comments (respect InputConfig mapping and format)
    logger.info(f"Loading comments from: {job.input.path} (format: {job.input.format})")
    comments = load_comments_from_config(job.input, limit=run_config.max_comments)
    logger.info(f"Loaded {len(comments)} comments")
    
    if not comments:
        # Return empty result if no comments
        logger.warning("No comments found, returning empty result")
        from ytce.ai.models.tokens import CostSummary
        result = AnalysisResult(
            enriched_comments=[],
            run_id=run_config.run_id,
            total_comments=0,
            total_tasks=len(job.tasks),
        )
        return result, CostSummary()
    
    # Step 1.5: Load or create checkpoint
    checkpoint: Optional[Checkpoint] = None
    if enable_checkpoint and checkpoint_dir and not is_preview:
        # Extract video_id from input path for checkpoint identification
        video_id = os.path.basename(os.path.dirname(job.input.path))
        
        # Try to load existing checkpoint
        existing_checkpoint = load_checkpoint(checkpoint_dir)
        if existing_checkpoint:
            logger.info(f"Found existing checkpoint with {sum(len(ids) for ids in existing_checkpoint.completed.values())} completed items")
            checkpoint = existing_checkpoint
        else:
            # Create new checkpoint
            task_ids = [task.id for task in job.tasks]
            checkpoint = create_checkpoint(
                video_id=video_id,
                total_comments=len(comments),
                task_ids=task_ids,
                run_id=run_config.run_id,
            )
            logger.info("Created new checkpoint")
            save_checkpoint(checkpoint, checkpoint_dir)
    
    # Step 2: Create model adapter
    logger.info(f"Creating model adapter: {run_config.model} (dry_run={run_config.dry_run})")
    model = create_adapter(
        model=run_config.model,
        api_key=run_config.api_key,
        dry_run=run_config.dry_run,
    )
    
    # Step 3: Execute all tasks and collect results
    # Structure: task_id -> comment_id -> TaskResult
    all_task_results: Dict[str, Dict[str, TaskResult]] = {}
    all_token_usages: List[TokenUsage] = []
    total_comments = len(comments)
    
    for task_idx, task in enumerate(job.tasks, 1):
        logger.info(f"Starting task {task_idx}/{len(job.tasks)}: {task.id} (type: {task.type.value})")
        task_results: Dict[str, TaskResult] = {}
        
        # Check if we need to resume for this task
        comments_to_process = comments
        if checkpoint:
            pending_comment_ids = checkpoint.get_pending_comments(task.id, [c.id for c in comments])
            if len(pending_comment_ids) < len(comments):
                logger.info(f"Resuming task {task.id}: {len(pending_comment_ids)}/{len(comments)} comments remaining")
                comments_to_process = [c for c in comments if c.id in pending_comment_ids]
                # Also load already completed results for this task (they're needed for final merge)
                # We'll handle this by tracking what's done in checkpoint
            elif len(pending_comment_ids) == 0:
                logger.info(f"Task {task.id} already completed, skipping")
                continue
        
        if not comments_to_process:
            logger.info(f"No comments to process for task {task.id}, skipping")
            continue
        
        # Adjust batch size for translation tasks (they need more tokens per comment)
        effective_batch_size = run_config.batch_size
        if task.type.value == "translation" and run_config.batch_size > 5:
            # Translation tasks are token-heavy, use smaller batches
            effective_batch_size = min(5, run_config.batch_size)
            logger.debug(f"Reduced batch size to {effective_batch_size} for translation task")
        
        # Cap batch size at 5 for all tasks
        if effective_batch_size > 5:
            logger.warning(f"Batch size {effective_batch_size} exceeds recommended max of 5, capping to 5")
            effective_batch_size = 5
        
        # Split comments into batches
        batches = batch_comments(comments_to_process, effective_batch_size)
        logger.info(f"Split into {len(batches)} batch(es) of size {effective_batch_size}")
        task_processed = 0
        
        # Execute task on each batch
        for batch_idx, batch in enumerate(batches, 1):
            logger.debug(f"Processing batch {batch_idx}/{len(batches)} ({len(batch)} comments)")
            try:
                batch_results, token_usage = execute_task(
                    task=task,
                    comments=batch,
                    model=model,
                    run_config=run_config,
                    custom_prompt=job.custom_prompt,
                )
                logger.debug(
                    f"Batch {batch_idx} completed: {len(batch_results)} results, "
                    f"tokens: {token_usage.prompt_tokens} input + {token_usage.completion_tokens} output"
                )
                # Merge batch results into task results
                task_results.update(batch_results)
                all_token_usages.append(token_usage)
                
                # Save checkpoint after each batch completes
                if checkpoint and checkpoint_dir:
                    batch_comment_ids = [c.id for c in batch]
                    checkpoint.mark_task_batch_complete(
                        task.id, 
                        batch_comment_ids,
                        batch_num=batch_idx,
                        total_batches=len(batches)
                    )
                    save_checkpoint(checkpoint, checkpoint_dir)
                    logger.debug(
                        f"Checkpoint saved: task={task.id}, batch={batch_idx}/{len(batches)}, "
                        f"comments={len(batch_comment_ids)}, total_batches_processed={checkpoint.total_batches_processed}"
                    )
                
                # Update progress - show progress for current task only.
                # We update per-comment (not per-batch) so the user sees 1/N, 2/N, ...
                if progress_callback:
                    for comment in batch:
                        # execute_task_base guarantees every comment in the batch has a result,
                        # so this is safe and keeps ordering stable.
                        if comment.id in batch_results:
                            task_processed += 1
                            progress_callback(
                                task_processed,
                                total_comments,
                                f"Task {task_idx}/{len(job.tasks)}: {task.id}",
                                is_preview,
                            )
            except TaskExecutionError as e:
                logger.error(f"Task execution failed for batch {batch_idx}: {str(e)}")
                # Re-raise with context
                raise TaskExecutionError(
                    f"Failed to execute task '{task.id}': {str(e)}"
                ) from e
        
        logger.info(f"Task {task_idx}/{len(job.tasks)} ({task.id}) completed: {len(task_results)} results")
        all_task_results[task.id] = task_results
    
    # Step 4: Merge results into EnrichedComment objects
    logger.info("Merging results into enriched comments")
    enriched_comments = _merge_results_into_comments(
        comments=comments,
        all_task_results=all_task_results,
    )
    
    # Step 5: Calculate cost summary
    cost_summary = aggregate_costs(all_token_usages, run_config.model)
    logger.info(
        f"Cost summary: ${cost_summary.total_cost:.4f} "
        f"({cost_summary.total_input_tokens:,} input + {cost_summary.total_output_tokens:,} output tokens)"
    )
    
    # Step 6: Return AnalysisResult and CostSummary
    result = AnalysisResult(
        enriched_comments=enriched_comments,
        run_id=run_config.run_id,
        total_comments=len(comments),
        total_tasks=len(job.tasks),
    )
    
    logger.info(f"Analysis complete: {len(enriched_comments)} comments, {len(job.tasks)} tasks")
    
    # Delete checkpoint on successful completion
    if checkpoint and checkpoint_dir:
        delete_checkpoint(checkpoint_dir)
    
    return result, cost_summary


def _merge_results_into_comments(
    comments: List[Comment],
    all_task_results: Dict[str, Dict[str, TaskResult]],
) -> List[EnrichedComment]:
    """
    Merge task results into EnrichedComment objects.
    
    Creates one EnrichedComment per comment, containing results from all tasks.
    
    Args:
        comments: Original list of comments
        all_task_results: Dictionary mapping task_id -> comment_id -> TaskResult
        
    Returns:
        List of EnrichedComment objects
    """
    # Create a mapping of comment_id -> comment for quick lookup
    comment_map = {c.id: c for c in comments}
    
    enriched_comments = []
    
    for comment in comments:
        # Collect all task results for this comment
        comment_results: Dict[str, TaskResult] = {}
        
        for task_id, task_results in all_task_results.items():
            if comment.id in task_results:
                comment_results[task_id] = task_results[comment.id]
        
        # Extract metadata from original comment
        metadata = {}
        if comment.author:
            metadata["author"] = comment.author
        if comment.channel:
            metadata["channel"] = comment.channel
        if comment.votes is not None:
            metadata["votes"] = comment.votes
        if comment.raw:
            metadata["raw"] = comment.raw
        
        # Create EnrichedComment
        enriched_comment = EnrichedComment(
            id=comment.id,
            text=comment.text,
            metadata=metadata if metadata else None,
            results=comment_results,
        )
        
        enriched_comments.append(enriched_comment)
    
    return enriched_comments


__all__ = [
    "run_analysis",
]

