from __future__ import annotations

import os
import shutil
import time
from datetime import datetime, timezone
from typing import Iterator, Optional

from ytce.__version__ import __version__
from ytce.storage.paths import channel_comments_dir, video_comments_filename
from ytce.storage.writers import ensure_dir, write_csv, write_json, write_jsonl, write_parquet, write_videos_csv, write_videos_parquet
from ytce.utils.progress import (
    ChannelProgressTracker,
    CommentProgressTracker,
    confirm_quit,
    format_number,
    print_step,
    print_success,
    print_video_progress,
    print_warning,
)
from ytce.youtube.channel_videos import YoutubeChannelVideosScraper
from ytce.youtube.comments import SORT_BY_POPULAR, SORT_BY_RECENT, YoutubeCommentDownloader


def _prepend_item(gen: Iterator, item):
    """Helper to prepend an item to a generator."""
    yield item
    yield from gen


def run(
    *,
    channel_id: str,
    out_dir: str,
    max_videos: Optional[int],
    sort: str,
    per_video_limit: Optional[int],
    language: Optional[str],
    debug: bool,
    dry_run: bool = False,
    format: str = "jsonl",
) -> None:
    # If directory exists, delete it to start fresh
    if os.path.exists(out_dir):
        print_step(f"Removing existing data for {channel_id}")
        shutil.rmtree(out_dir)
    
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
    videos_data = {
        "channel_id": channel_id,
        "total_videos": len(videos),
        "videos": videos,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source": f"ytce/{__version__}",
    }
    
    if format == "csv":
        videos_path = os.path.join(out_dir, "videos.csv")
        write_videos_csv(videos_path, videos_data)
    elif format == "parquet":
        videos_path = os.path.join(out_dir, "videos.parquet")
        write_videos_parquet(videos_path, videos_data)
    else:
        videos_path = os.path.join(out_dir, "videos.json")
        write_json(videos_path, videos_data)
    
    # Track videos file size
    videos_file_size = os.path.getsize(videos_path) if os.path.exists(videos_path) else 0
    
    print()

    # 2) Comments per video
    cd = YoutubeCommentDownloader()
    sort_by = SORT_BY_RECENT if sort == "recent" else SORT_BY_POPULAR
    
    print_step("Processing videos")
    
    # Create channel-level progress tracker
    channel_tracker = ChannelProgressTracker(len(videos), per_video_limit=per_video_limit)
    
    # Show initial channel statistics
    if len(videos) > 1:
        print(f"  📊 {channel_tracker.get_statistics()}", flush=True)
    print()

    idx = 0
    while idx < len(videos):
        try:
            v = videos[idx]
            video_id = v["video_id"]
            order = v.get("order", 0)
            safe_name = video_comments_filename(order, video_id, format=format)
            out_path = os.path.join(comments_dir, safe_name)

            try:
                video_start_time = time.time()
                
                gen = cd.get_comments(video_id, sort_by=sort_by, language=language, sleep=0.1)
                scraped_at = datetime.now(timezone.utc).isoformat()

                # Extract total comment count from generator (first item might be metadata)
                total_count = None
                first_item = next(gen, None)
                if first_item and isinstance(first_item, dict) and "_total_count" in first_item:
                    total_count = first_item["_total_count"]
                    # Use per_video_limit if set, otherwise use discovered total
                    expected_total = per_video_limit if per_video_limit is not None else total_count
                else:
                    expected_total = per_video_limit
                    # Put first item back into generator
                    if first_item:
                        gen = _prepend_item(gen, first_item)

                # Create progress tracker for real-time updates with expected total
                progress_tracker = CommentProgressTracker(
                    video_id, 
                    order, 
                    len(videos),
                    expected_total=expected_total,
                )

                def limited():
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
                        if per_video_limit is not None and count >= per_video_limit:
                            break

                if format == "csv":
                    # Use progress callback for real-time updates
                    wrote = write_csv(out_path, limited(), progress_callback=progress_tracker.update)
                elif format == "parquet":
                    # For Parquet, also track progress
                    wrote = write_parquet(out_path, limited(), progress_callback=progress_tracker.update)
                else:
                    # For JSONL, also track progress
                    wrote = write_jsonl(out_path, limited(), progress_callback=progress_tracker.update)
                
                # Calculate elapsed time for this video
                video_elapsed = time.time() - video_start_time
                
                # Print final progress
                progress_tracker.finish(wrote)
                
                # Get file size
                file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
                
                # Update channel tracker
                channel_tracker.video_completed(order, wrote, video_elapsed, file_size)
                
                # Print channel-level statistics every 5 videos or on last video
                if order % 5 == 0 or order == len(videos):
                    stats = channel_tracker.get_statistics()
                    print(f"  📊 {stats}", flush=True)
            except Exception as e:
                if "comments disabled" in str(e).lower():
                    print_video_progress(order, len(videos), video_id, status="comments disabled")
                else:
                    print_video_progress(order, len(videos), video_id, status=f"error: {e}")
                    if debug:
                        raise
            
            # Move to next video
            idx += 1
            
        except KeyboardInterrupt:
            # User pressed Ctrl+C - ask for confirmation
            if confirm_quit():
                print()
                print_warning("Scraping cancelled by user")
                print_warning(f"Partial data saved to {out_dir}/")
                print_warning("⚠️  Remember: Restarting this channel will delete all existing data!")
                return
            else:
                # User changed their mind - continue the loop
                print()
                print_success("Continuing scrape...")
                print()
                # Loop will continue with next video

    print()
    # Show final channel statistics (add videos file size to total)
    channel_tracker.total_bytes += videos_file_size
    print(channel_tracker.get_final_statistics())
    print()
    print_success("Done!")
    print_success(f"Output: {out_dir}/")
