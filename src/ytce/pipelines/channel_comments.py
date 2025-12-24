from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from ytce.__version__ import __version__
from ytce.storage.paths import channel_comments_dir, video_comments_filename
from ytce.storage.resume import should_skip_existing
from ytce.storage.writers import ensure_dir, write_csv, write_json, write_jsonl, write_videos_csv
from ytce.utils.progress import format_number, print_step, print_success, print_video_progress
from ytce.youtube.channel_videos import YoutubeChannelVideosScraper
from ytce.youtube.comments import SORT_BY_POPULAR, SORT_BY_RECENT, YoutubeCommentDownloader


def run(
    *,
    channel_id: str,
    out_dir: str,
    max_videos: Optional[int],
    sort: str,
    per_video_limit: Optional[int],
    language: Optional[str],
    resume: bool,
    debug: bool,
    dry_run: bool = False,
    format: str = "jsonl",
) -> None:
    ensure_dir(out_dir)
    comments_dir = channel_comments_dir(out_dir)
    ensure_dir(comments_dir)

    # 1) Videos metadata
    print_step(f"Fetching channel: {channel_id}")
    vs = YoutubeChannelVideosScraper(debug=debug)
    videos = vs.get_all_videos(channel_id, max_videos=max_videos, show_progress=False)
    print_success(f"Found {format_number(len(videos))} videos")
    
    if dry_run:
        # Calculate dry-run statistics
        videos_with_comments = sum(1 for v in videos if v.get("has_comments", True))
        estimated_comments = videos_with_comments * (per_video_limit if per_video_limit else 500)
        
        print()
        print_success(f"{format_number(len(videos))} videos found")
        print_success(f"~{format_number(videos_with_comments)} videos with comments")
        if per_video_limit:
            print_success(f"~{format_number(estimated_comments)} comments will be downloaded (limited to {per_video_limit} per video)")
        else:
            print_success(f"~{format_number(estimated_comments)} comments will be downloaded (estimate)")
        print_success("No files written (dry-run mode)")
        return
    
    # Write videos metadata
    if format == "csv":
        videos_path = os.path.join(out_dir, "videos.csv")
        videos_data = {
            "channel_id": channel_id,
            "total_videos": len(videos),
            "videos": videos,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source": f"ytce/{__version__}",
        }
        write_videos_csv(videos_path, videos_data)
    else:
        videos_path = os.path.join(out_dir, "videos.json")
        videos_data = {
            "channel_id": channel_id,
            "total_videos": len(videos),
            "videos": videos,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source": f"ytce/{__version__}",
        }
        write_json(videos_path, videos_data)
    print()

    # 2) Comments per video
    cd = YoutubeCommentDownloader()
    sort_by = SORT_BY_RECENT if sort == "recent" else SORT_BY_POPULAR
    
    # Check how many videos already have comments
    existing_count = sum(
        1 for v in videos
        if should_skip_existing(
            os.path.join(comments_dir, video_comments_filename(v.get("order", 0), v["video_id"])),
            resume=resume
        )
    )
    
    if existing_count > 0 and resume:
        print_step(f"Resuming from video {existing_count + 1:03d} ({existing_count} already downloaded)")
    else:
        print_step("Processing videos")

    for v in videos:
        video_id = v["video_id"]
        order = v.get("order", 0)
        safe_name = video_comments_filename(order, video_id, format=format)
        out_path = os.path.join(comments_dir, safe_name)

        if should_skip_existing(out_path, resume=resume):
            continue

        try:
            gen = cd.get_comments(video_id, sort_by=sort_by, language=language, sleep=0.1)
            scraped_at = datetime.now(timezone.utc).isoformat()

            def limited():
                count = 0
                for c in gen:
                    # Add metadata to each comment
                    comment_data = dict(c) if isinstance(c, dict) else c.__dict__
                    comment_data["scraped_at"] = scraped_at
                    comment_data["source"] = f"ytce/{__version__}"
                    yield comment_data
                    count += 1
                    if per_video_limit is not None and count >= per_video_limit:
                        break

            if format == "csv":
                wrote = write_csv(out_path, limited())
            else:
                wrote = write_jsonl(out_path, limited())
            print_video_progress(order, len(videos), video_id, comment_count=wrote)
        except Exception as e:
            if "comments disabled" in str(e).lower():
                print_video_progress(order, len(videos), video_id, status="comments disabled")
            else:
                print_video_progress(order, len(videos), video_id, status=f"error: {e}")
                if debug:
                    raise

    print()
    print_success("Done")
    print_success(f"Saved to {out_dir}/")
