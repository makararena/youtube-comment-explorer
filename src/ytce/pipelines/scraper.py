"""Core channel scraping logic - reusable for single and batch operations."""
from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ytce.__version__ import __version__
from ytce.models.batch import ChannelStats
from ytce.storage.paths import channel_comments_dir, channel_output_dir, video_comments_filename
from ytce.storage.writers import (
    ensure_dir,
    write_csv,
    write_json,
    write_jsonl,
    write_parquet,
    write_videos_csv,
    write_videos_parquet,
)
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


@dataclass
class ScrapeConfig:
    """Configuration for channel scraping."""
    
    channel_id: str
    out_dir: Optional[str] = None
    base_dir: str = "data"
    max_videos: Optional[int] = None
    per_video_limit: Optional[int] = None
    sort: str = "recent"
    language: str = "en"
    format: str = "jsonl"
    debug: bool = False
    videos_only: bool = False
    dry_run: bool = False
    quiet: bool = False  # For batch mode


def scrape_channel(config: ScrapeConfig) -> ChannelStats:
    """
    Scrape a single channel with all its videos and comments.
    
    This is the core scraping function used by both `ytce channel` and `ytce batch`.
    
    Args:
        config: Scraping configuration
    
    Returns:
        ChannelStats with results
    
    Raises:
        Exception: On scraping errors (caller should handle)
    """
    start_time = time.time()
    
    # Determine output directory
    if config.out_dir:
        out_dir = config.out_dir
    else:
        out_dir = channel_output_dir(config.channel_id, base_dir=config.base_dir)
    
    # If directory exists, delete it to start fresh
    if os.path.exists(out_dir):
        if not config.quiet:
            print_step(f"Removing existing data for {config.channel_id}")
        shutil.rmtree(out_dir)
    
    ensure_dir(out_dir)
    comments_dir = channel_comments_dir(out_dir)
    ensure_dir(comments_dir)
    
    # 1) Fetch videos metadata
    if not config.quiet:
        print_step(f"Fetching channel: {config.channel_id}")
    
    vs = YoutubeChannelVideosScraper(debug=config.debug)
    videos = vs.get_all_videos(config.channel_id, max_videos=config.max_videos, show_progress=False)
    
    if not config.quiet:
        print_success(f"Found {format_number(len(videos))} videos")
    
    # Dry run
    if config.dry_run:
        videos_with_comments = sum(1 for v in videos if v.get("has_comments", True))
        
        if not config.quiet:
            print()
            print_success(f"{format_number(len(videos))} videos found")
            print_success(f"~{format_number(videos_with_comments)} videos with comments")
            print_success("No files written (dry-run mode)")
        
        return ChannelStats(
            channel=config.channel_id,
            videos=len(videos),
            comments=0,  # Unknown in dry-run mode
            bytes_mb=0.0,
            duration_sec=time.time() - start_time,
            status="ok",
        )
    
    # Write videos metadata
    videos_data = {
        "channel_id": config.channel_id,
        "total_videos": len(videos),
        "videos": videos,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source": f"ytce/{__version__}",
    }
    
    if config.format == "csv":
        videos_path = os.path.join(out_dir, "videos.csv")
        write_videos_csv(videos_path, videos_data)
    elif config.format == "parquet":
        videos_path = os.path.join(out_dir, "videos.parquet")
        write_videos_parquet(videos_path, videos_data)
    else:
        videos_path = os.path.join(out_dir, "videos.json")
        write_json(videos_path, videos_data)
    
    # Track videos file size
    videos_file_size = os.path.getsize(videos_path) if os.path.exists(videos_path) else 0
    
    # If videos only, return early
    if config.videos_only:
        duration = time.time() - start_time
        return ChannelStats(
            channel=config.channel_id,
            videos=len(videos),
            comments=0,
            bytes_mb=videos_file_size / (1024 * 1024),
            duration_sec=duration,
            status="ok",
        )
    
    if not config.quiet:
        print()
    
    # 2) Download comments for each video
    cd = YoutubeCommentDownloader()
    sort_by = SORT_BY_RECENT if config.sort == "recent" else SORT_BY_POPULAR
    
    if not config.quiet:
        print_step("Processing videos")
        
        # Create channel-level progress tracker
        channel_tracker = ChannelProgressTracker(len(videos), per_video_limit=config.per_video_limit)
        
        # Show initial channel statistics
        if len(videos) > 1:
            print(f"  📊 {channel_tracker.get_statistics()}", flush=True)
        print()
    
    total_comments = 0
    total_bytes = videos_file_size
    
    idx = 0
    while idx < len(videos):
        try:
            v = videos[idx]
            video_id = v["video_id"]
            order = v.get("order", 0)
            safe_name = video_comments_filename(order, video_id, format=config.format)
            out_path = os.path.join(comments_dir, safe_name)
            
            try:
                video_start_time = time.time()
                
                gen = cd.get_comments(video_id, sort_by=sort_by, language=config.language, sleep=0.1)
                scraped_at = datetime.now(timezone.utc).isoformat()
                
                # Extract total comment count from generator
                total_count = None
                first_item = next(gen, None)
                if first_item and isinstance(first_item, dict) and "_total_count" in first_item:
                    total_count = first_item["_total_count"]
                    expected_total = config.per_video_limit if config.per_video_limit is not None else total_count
                else:
                    expected_total = config.per_video_limit
                    if first_item:
                        def _prepend_item(gen, item):
                            yield item
                            yield from gen
                        gen = _prepend_item(gen, first_item)
                
                # Create progress tracker
                if not config.quiet:
                    progress_tracker = CommentProgressTracker(
                        video_id,
                        order,
                        len(videos),
                        expected_total=expected_total,
                    )
                
                def limited():
                    count = 0
                    for c in gen:
                        if isinstance(c, dict) and "_total_count" in c:
                            continue
                        comment_data = dict(c) if isinstance(c, dict) else c.__dict__
                        comment_data["scraped_at"] = scraped_at
                        comment_data["source"] = f"ytce/{__version__}"
                        yield comment_data
                        count += 1
                        if config.per_video_limit is not None and count >= config.per_video_limit:
                            break
                
                # Write comments
                if config.format == "csv":
                    wrote = write_csv(
                        out_path,
                        limited(),
                        progress_callback=progress_tracker.update if not config.quiet else None
                    )
                elif config.format == "parquet":
                    wrote = write_parquet(
                        out_path,
                        limited(),
                        progress_callback=progress_tracker.update if not config.quiet else None
                    )
                else:
                    wrote = write_jsonl(
                        out_path,
                        limited(),
                        progress_callback=progress_tracker.update if not config.quiet else None
                    )
                
                video_elapsed = time.time() - video_start_time
                total_comments += wrote
                
                # Print progress
                if not config.quiet:
                    progress_tracker.finish(wrote)
                
                # Get file size
                file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
                total_bytes += file_size
                
                # Update channel tracker
                if not config.quiet:
                    channel_tracker.video_completed(order, wrote, video_elapsed, file_size)
                    
                    # Print channel-level statistics
                    if order % 5 == 0 or order == len(videos):
                        stats = channel_tracker.get_statistics()
                        print(f"  📊 {stats}", flush=True)
            
            except Exception as e:
                if "comments disabled" in str(e).lower():
                    if not config.quiet:
                        print_video_progress(order, len(videos), video_id, status="comments disabled")
                else:
                    if not config.quiet:
                        print_video_progress(order, len(videos), video_id, status=f"error: {e}")
                    if config.debug:
                        raise
            
            idx += 1
        
        except KeyboardInterrupt:
            if not config.quiet and confirm_quit():
                print()
                print_warning("Scraping cancelled by user")
                print_warning(f"Partial data saved to {out_dir}/")
                raise
            else:
                if not config.quiet:
                    print()
                    print_success("Continuing scrape...")
                    print()
    
    duration = time.time() - start_time
    
    if not config.quiet:
        print()
        channel_tracker.total_bytes = total_bytes
        print(channel_tracker.get_final_statistics())
        print()
        print_success("Done!")
        print_success(f"Output: {out_dir}/")
    
    return ChannelStats(
        channel=config.channel_id,
        videos=len(videos),
        comments=total_comments,
        bytes_mb=total_bytes / (1024 * 1024),
        duration_sec=duration,
        status="ok",
    )

