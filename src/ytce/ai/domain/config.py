from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class RunConfig:
    """
    Runtime configuration for a single AI analysis run.

    DOMAIN object:
    - immutable
    - no execution logic
    - no validation logic
    - describes HOW the analysis is executed, not WHAT is analyzed
    """

    # LLM model identifier (e.g. "gpt-4.1-nano", "gpt-4.1-mini", etc.)
    model: str

    # API key provided by the user
    api_key: str

    # Number of comments per LLM request
    batch_size: int = 20

    # Sampling temperature for the model
    temperature: float = 0.0

    # If True, skip actual LLM calls (used for previews / testing)
    dry_run: bool = False

    # Optional limit on number of comments to load/process (used for preview runs)
    max_comments: Optional[int] = None

    # Maximum characters per comment text (longer comments will be truncated)
    # None means no truncation
    max_comment_length: Optional[int] = None

    # Optional run identifier (for logging / tracing)
    run_id: Optional[str] = None

__all__ = [
    "RunConfig"
]
