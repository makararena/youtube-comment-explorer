"""Batch scraping pipeline for multiple channels."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import List, Optional

from ytce.models.batch import BatchReport, ChannelStats
from ytce.pipelines.scraper import ScrapeConfig, scrape_channel
from ytce.utils.channels import parse_channels_file
from ytce.utils.progress import format_bytes, format_duration, format_number, print_error, print_step, print_success, print_warning


def run_batch(
    *,
    channels_file: str,
    base_dir: str = "data",
    max_videos: Optional[int] = None,
    per_video_limit: Optional[int] = None,
    sort: str = "recent",
    language: str = "en",
    format: str = "jsonl",
    debug: bool = False,
    fail_fast: bool = False,
    dry_run: bool = False,
    sleep_between: int = 2,
) -> Optional[BatchReport]:
    """
    Run batch scraping for multiple channels.
    
    Args:
        channels_file: Path to file containing channel list
        base_dir: Base directory for outputs
        max_videos: Limit videos per channel
        per_video_limit: Limit comments per video
        sort: Comment sort order
        language: Language code
        format: Output format (json/csv/parquet)
        debug: Enable debug output
        fail_fast: Stop on first error
        dry_run: Preview only, don't download
        sleep_between: Seconds to sleep between channels
    
    Returns:
        BatchReport with results, or None if interrupted by user
    """
    started_at = datetime.now(timezone.utc)
    
    # Parse channels file
    print_step(f"Reading channels from: {channels_file}")
    try:
        channels = parse_channels_file(channels_file)
    except FileNotFoundError:
        print_error(f"File not found: {channels_file}")
        raise
    
    if not channels:
        print_error("No valid channels found in file")
        raise ValueError("No channels to process")
    
    print_success(f"Found {len(channels)} channel(s) to process")
    print()
    
    # Create batch output directory
    batch_dir = os.path.join(base_dir, "_batch", started_at.strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(batch_dir, exist_ok=True)
    
    # Copy channels file as snapshot
    import shutil
    shutil.copy(channels_file, os.path.join(batch_dir, "channels.txt"))
    
    # Open errors log
    errors_log = os.path.join(batch_dir, "errors.log")
    
    # Process each channel
    stats_list: List[ChannelStats] = []
    
    for idx, channel in enumerate(channels, 1):
        print_step(f"[{idx}/{len(channels)}] Processing: {channel}")
        
        config = ScrapeConfig(
            channel_id=channel,
            base_dir=base_dir,
            max_videos=max_videos,
            per_video_limit=per_video_limit,
            sort=sort,
            language=language,
            format=format,
            debug=debug,
            dry_run=dry_run,
            quiet=False,
        )
        
        try:
            stats = scrape_channel(config)
            stats_list.append(stats)
            
            # Print summary
            if stats.status == "ok":
                print_success(
                    f"[{idx}/{len(channels)}] {channel} — "
                    f"{format_number(stats.videos)} videos — "
                    f"{format_number(stats.comments)} comments — "
                    f"OK ({format_bytes(stats.bytes_mb * 1024 * 1024)}, {format_duration(stats.duration_sec)})"
                )
            
            # Sleep between channels (except last one)
            if idx < len(channels) and sleep_between > 0:
                time.sleep(sleep_between)
        
        except KeyboardInterrupt:
            print()
            print_warning("Batch interrupted by user")
            # Save partial results and exit gracefully
            if stats_list:
                finished_at = datetime.now(timezone.utc)
                report = _create_batch_report(started_at, finished_at, stats_list, channels)
                _write_batch_report(batch_dir, started_at, stats_list, channels)
                _print_final_summary(report)
                print_success(f"Partial results saved to: {batch_dir}/")
            return None  # Signal interruption
        
        except Exception as e:
            error_msg = str(e)
            print_error(f"[{idx}/{len(channels)}] {channel} — ERROR: {error_msg}")
            
            # Log error to file
            with open(errors_log, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now(timezone.utc).isoformat()} | {channel} | {error_msg}\n")
            
            # Record failed stats
            stats_list.append(
                ChannelStats(
                    channel=channel,
                    status="failed",
                    error=error_msg,
                )
            )
            
            if fail_fast:
                print_error("Stopping batch due to --fail-fast")
                break
        
        print()
    
    # Generate report
    finished_at = datetime.now(timezone.utc)
    report = _create_batch_report(started_at, finished_at, stats_list, channels)
    
    # Write report
    _write_batch_report(batch_dir, started_at, stats_list, channels)
    
    # Print final summary
    _print_final_summary(report)
    
    print_success(f"Batch artifacts saved to: {batch_dir}/")
    
    return report


def _create_batch_report(
    started_at: datetime,
    finished_at: datetime,
    stats_list: List[ChannelStats],
    all_channels: List[str],
) -> BatchReport:
    """Create batch report from stats."""
    channels_ok = sum(1 for s in stats_list if s.status == "ok")
    channels_failed = len(stats_list) - channels_ok
    
    total_videos = sum(s.videos for s in stats_list if s.status == "ok")
    total_comments = sum(s.comments for s in stats_list if s.status == "ok")
    total_bytes_mb = sum(s.bytes_mb for s in stats_list if s.status == "ok")
    total_duration = (finished_at - started_at).total_seconds()
    
    stats_dicts = []
    for s in stats_list:
        if s.status == "ok":
            stats_dicts.append({
                "channel": s.channel,
                "videos": s.videos,
                "comments": s.comments,
                "bytes_mb": round(s.bytes_mb, 2),
                "duration_sec": round(s.duration_sec, 1),
                "status": "ok",
            })
        else:
            stats_dicts.append({
                "channel": s.channel,
                "status": "failed",
                "error": s.error,
            })
    
    return BatchReport(
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        channels_total=len(all_channels),
        channels_ok=channels_ok,
        channels_failed=channels_failed,
        total_videos=total_videos,
        total_comments=total_comments,
        total_bytes_mb=total_bytes_mb,
        total_duration_sec=total_duration,
        stats=stats_dicts,
    )


def _write_batch_report(
    batch_dir: str,
    started_at: datetime,
    stats_list: List[ChannelStats],
    all_channels: List[str],
) -> None:
    """Write batch report to JSON file."""
    finished_at = datetime.now(timezone.utc)
    report = _create_batch_report(started_at, finished_at, stats_list, all_channels)
    
    report_path = os.path.join(batch_dir, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)


def _print_final_summary(report: BatchReport) -> None:
    """Print beautiful final summary."""
    print()
    print("━" * 60)
    print("Batch completed")
    print("━" * 60)
    print(f"✔ Channels OK:     {report.channels_ok}")
    if report.channels_failed > 0:
        print(f"✖ Channels failed: {report.channels_failed}")
    print(f"📼 Total videos:   {format_number(report.total_videos)}")
    print(f"💬 Total comments: {format_number(report.total_comments)}")
    print(f"📦 Total data:     {format_bytes(report.total_bytes_mb * 1024 * 1024)}")
    print(f"⏱ Total time:     {format_duration(report.total_duration_sec)}")
    print("━" * 60)
    print()

