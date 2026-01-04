from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

@dataclass(frozen=True)
class TaskResult:
    """
    Result of a single task for a single comment.

    DOMAIN object:
    - contains no execution logic
    - contains no formatting logic
    - represents a normalized, structured outcome
    """

    # The actual result value.
    #
    # Possible types:
    # - str           → binary / multi_class
    # - List[str]     → multi_label
    # - float         → scoring
    value: Union[str, List[str], float]

    # Optional confidence score provided by the model.
    # Range is expected to be [0.0, 1.0], but this is NOT enforced here.
    confidence: Optional[float] = None

@dataclass(frozen=True)
class EnrichedComment:
    """
    Comment enriched with results of all analysis tasks.
    """

    id: str
    text: str

    # Original metadata passed through the system unchanged
    metadata: Optional[Dict] = None

    # Mapping: task_id -> TaskResult
    results: Dict[str, TaskResult] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisResult:
    """
    Complete result of an AI analysis run.
    
    Contains all enriched comments with their task results.
    """
    
    # List of comments enriched with analysis results
    enriched_comments: List[EnrichedComment]
    
    # Optional metadata about the run
    run_id: Optional[str] = None
    
    # Statistics about the analysis
    total_comments: int = 0
    total_tasks: int = 0
    
    def __post_init__(self):
        """Set statistics if not provided."""
        if self.total_comments == 0:
            object.__setattr__(self, "total_comments", len(self.enriched_comments))
        if self.total_tasks == 0 and self.enriched_comments:
            # Count unique task IDs from first comment
            first_comment = self.enriched_comments[0]
            if first_comment.results:
                object.__setattr__(self, "total_tasks", len(first_comment.results))


__all__ = [
    "TaskResult",
    "EnrichedComment",
    "AnalysisResult",
]
