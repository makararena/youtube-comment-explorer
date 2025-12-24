from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from ytce.__version__ import __version__
from ytce.storage.writers import write_csv, write_jsonl
from ytce.utils.progress import CommentProgressTracker, format_number, print_step, print_success
from ytce.youtube.comments import SORT_BY_POPULAR, SORT_BY_RECENT, YoutubeCommentDownloader


def run(
    *,
    video_id: str,
    output: str,
    sort: str,
    limit: Optional[int],
    language: Optional[str],
    format: str = "jsonl",
) -> None:
    print_step(f"Fetching comments for video: {video_id}")
    downloader = YoutubeCommentDownloader()
    sort_by = SORT_BY_RECENT if sort == "recent" else SORT_BY_POPULAR

    gen = downloader.get_comments(video_id, sort_by=sort_by, language=language, sleep=0.1)
    scraped_at = datetime.now(timezone.utc).isoformat()

    # Extract total comment count from generator (first item might be metadata)
    total_count = None
    first_item = next(gen, None)
    if first_item and isinstance(first_item, dict) and "_total_count" in first_item:
        total_count = first_item["_total_count"]
        # Use limit if set, otherwise use discovered total
        expected_total = limit if limit is not None else total_count
    else:
        expected_total = limit
        # Put first item back into generator
        if first_item:
            def _prepend_item(gen, item):
                yield item
                yield from gen
            gen = _prepend_item(gen, first_item)

    # Create progress tracker for real-time updates with expected total
    progress_tracker = CommentProgressTracker(video_id, 1, 1, expected_total=expected_total)

    def limited():
        nonlocal gen
        count = 0
        for c in gen:
            # Skip metadata items
            if isinstance(c, dict) and "_total_count" in c:
                continue
            # Add metadata to each comment
            comment_data = dict(c) if isinstance(c, dict) else c.__dict__
            comment_data["scraped_at"] = scraped_at
            comment_data["source"] = f"ytce/{__version__}"
            yield comment_data
            count += 1
            if limit is not None and count >= limit:
                break

    if format == "csv":
        wrote = write_csv(output, limited(), progress_callback=progress_tracker.update)
    else:
        wrote = write_jsonl(output, limited(), progress_callback=progress_tracker.update)
    
    # Print final progress
    progress_tracker.finish(wrote)
    print_success(f"Saved to {output}")
