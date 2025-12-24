"""Progress and status output utilities for better UX."""

from __future__ import annotations

import sys
import time
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


def confirm_quit() -> bool:
    """
    Ask user to confirm if they want to quit the scraping process.
    
    Returns:
        True if user wants to quit, False otherwise
    """
    print("\n")
    print("⚠️  STOPPING SCRAPE")
    print("━" * 60)
    print("⚠️  If you quit now and restart the channel download later,")
    print("   ALL existing data will be deleted and re-downloaded from scratch.")
    print("━" * 60)
    print()
    
    try:
        response = input("Do you really want to quit? [y/N]: ").strip().lower()
        return response in ["y", "yes"]
    except (EOFError, KeyboardInterrupt):
        # If they Ctrl+C again during prompt, assume yes
        print("\nQuitting...")
        return True


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


def format_time(seconds: float) -> str:
    """Format seconds into human-readable time string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_bytes(bytes_size: int) -> str:
    """Format bytes into human-readable size string."""
    if bytes_size < 1024:
        return f"{bytes_size}B"
    elif bytes_size < 1024 * 1024:
        kb = bytes_size / 1024
        return f"{kb:.1f}KB"
    elif bytes_size < 1024 * 1024 * 1024:
        mb = bytes_size / (1024 * 1024)
        return f"{mb:.1f}MB"
    else:
        gb = bytes_size / (1024 * 1024 * 1024)
        return f"{gb:.2f}GB"


class CommentProgressTracker:
    """Tracks and displays real-time comment export progress with ETA."""
    
    def __init__(
        self, 
        video_id: str, 
        video_index: int, 
        total_videos: int,
        expected_total: Optional[int] = None,
    ):
        self.video_id = video_id
        self.video_index = video_index
        self.total_videos = total_videos
        self.expected_total = expected_total  # Expected total comments for this video
        self.count = 0
        self._start_time = time.time()
        self._last_printed = 0
        self._last_time = self._start_time
        # Print every 50 comments for better performance (adjust as needed)
        self._print_interval = 50
    
    def update(self, count: int) -> None:
        """Update progress counter and print if needed."""
        self.count = count
        current_time = time.time()
        
        # Print on first update, then every N comments or every 2 seconds
        time_since_last_print = current_time - self._last_time
        should_print = (
            count == 1 or 
            count - self._last_printed >= self._print_interval or
            time_since_last_print >= 2.0
        )
        
        if should_print:
            self._print_progress()
            self._last_printed = count
            self._last_time = current_time
    
    def _calculate_eta(self) -> Optional[str]:
        """Calculate estimated time remaining."""
        if self.count == 0:
            return None
        
        elapsed = time.time() - self._start_time
        if elapsed < 1.0:  # Need at least 1 second of data
            return None
        
        comments_per_sec = self.count / elapsed
        
        if self.expected_total:
            remaining = self.expected_total - self.count
            if remaining <= 0:
                return "almost done"
            eta_seconds = remaining / comments_per_sec
            return format_time(eta_seconds)
        else:
            # If we don't know total, estimate based on current rate
            # Estimate conservatively (assume similar rate continues)
            return None
    
    def _calculate_percentage(self) -> Optional[str]:
        """Calculate percentage complete."""
        if self.expected_total and self.expected_total > 0:
            percentage = (self.count / self.expected_total) * 100
            return f"{percentage:.1f}%"
        return None
    
    def _print_progress(self) -> None:
        """Print progress with percentage and ETA."""
        parts = [f"[{self.video_index:03d}/{self.total_videos:03d}] {self.video_id}"]
        
        # Add count with expected total if available
        if self.expected_total:
            parts.append(f"{self.count:,}/{self.expected_total:,} comments")
        else:
            parts.append(f"{self.count:,} comments")
        
        # Add percentage
        percentage = self._calculate_percentage()
        if percentage:
            parts.append(f"({percentage})")
        
        # Add ETA
        eta = self._calculate_eta()
        if eta:
            parts.append(f"- ETA: {eta}")
        
        progress_str = " — ".join(parts) + "\r"
        print(progress_str, end="", flush=True)
    
    def finish(self, final_count: int) -> None:
        """Print final progress and move to next line."""
        self.count = final_count
        elapsed = time.time() - self._start_time
        
        parts = [f"[{self.video_index:03d}/{self.total_videos:03d}] {self.video_id}"]
        
        if self.expected_total:
            parts.append(f"{final_count:,}/{self.expected_total:,} comments")
        else:
            parts.append(f"{final_count:,} comments")
        
        # Add elapsed time
        elapsed_str = format_time(elapsed)
        parts.append(f"in {elapsed_str}")
        
        final_str = " — ".join(parts)
        print(final_str, flush=True)


class ChannelProgressTracker:
    """Tracks overall channel export progress across multiple videos."""
    
    def __init__(self, total_videos: int, per_video_limit: Optional[int] = None):
        self.total_videos = total_videos
        self.per_video_limit = per_video_limit
        self.videos_completed = 0
        self.total_comments = 0
        self.total_bytes = 0
        self._start_time = time.time()
        self._video_times = []  # Track time per video for better ETA
    
    def video_started(self, video_index: int) -> None:
        """Called when a video starts processing."""
        pass
    
    def video_completed(self, video_index: int, comment_count: int, elapsed_time: float, file_size: int = 0) -> None:
        """Called when a video completes."""
        self.videos_completed += 1
        self.total_comments += comment_count
        self.total_bytes += file_size
        self._video_times.append(elapsed_time)
    
    def get_eta(self) -> Optional[str]:
        """Calculate ETA for remaining videos."""
        if self.videos_completed == 0:
            return None
        
        remaining_videos = self.total_videos - self.videos_completed
        if remaining_videos <= 0:
            return None
        
        # Use average time per video for ETA
        if self._video_times:
            avg_time_per_video = sum(self._video_times) / len(self._video_times)
            eta_seconds = avg_time_per_video * remaining_videos
            return format_time(eta_seconds)
        return None
    
    def get_statistics(self) -> str:
        """Get formatted statistics string."""
        elapsed = time.time() - self._start_time
        elapsed_str = format_time(elapsed)
        
        # Calculate percentage of videos completed
        percentage = (self.videos_completed / self.total_videos * 100) if self.total_videos > 0 else 0
        
        parts = [
            f"Videos: {self.videos_completed}/{self.total_videos} ({percentage:.1f}%)",
            f"Comments: {format_number(self.total_comments)}",
            f"Data: {format_bytes(self.total_bytes)}",
            f"Time: {elapsed_str}",
        ]
        
        eta = self.get_eta()
        if eta:
            parts.append(f"ETA: {eta}")
        
        return " | ".join(parts)
    
    def get_final_statistics(self) -> str:
        """Get final summary statistics."""
        elapsed = time.time() - self._start_time
        elapsed_str = format_time(elapsed)
        
        lines = [
            "📊 FINAL STATISTICS",
            "━" * 60,
            f"  Total Videos:   {format_number(self.videos_completed)}",
            f"  Total Comments: {format_number(self.total_comments)}",
            f"  Total Data:     {format_bytes(self.total_bytes)}",
            f"  Total Time:     {elapsed_str}",
            "━" * 60,
        ]
        
        return "\n".join(lines)

