"""Progress and status output utilities for better UX."""

from __future__ import annotations

import sys
from typing import Optional


def print_step(message: str) -> None:
    """Print a step in progress."""
    print(f"▶ {message}", flush=True)


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"✔ {message}", flush=True)


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"⚠ {message}", flush=True)


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"✗ {message}", file=sys.stderr, flush=True)


def print_video_progress(index: int, total: int, video_id: str, comment_count: Optional[int] = None, status: str = "") -> None:
    """Print progress for video processing."""
    if comment_count is not None:
        count_str = f"{comment_count:,} comments"
    else:
        count_str = status
    
    print(f"[{index:03d}/{total:03d}] {video_id} — {count_str}", flush=True)


def format_number(num: int) -> str:
    """Format a number with thousands separator."""
    return f"{num:,}"

