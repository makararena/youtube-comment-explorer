from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ytce.__version__ import __version__
from ytce.storage.writers import write_csv, write_jsonl
from ytce.utils.progress import format_number, print_step, print_success
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

    def limited():
        nonlocal gen
        count = 0
        for c in gen:
            # Add metadata to each comment
            comment_data = dict(c) if isinstance(c, dict) else c.__dict__
            comment_data["scraped_at"] = scraped_at
            comment_data["source"] = f"ytce/{__version__}"
            yield comment_data
            count += 1
            if limit is not None and count >= limit:
                break

    if format == "csv":
        wrote = write_csv(output, limited())
    else:
        wrote = write_jsonl(output, limited())
    print_success(f"Downloaded {format_number(wrote)} comments")
    print_success(f"Saved to {output}")
