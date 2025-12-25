from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class ChannelStats:
    """Statistics from scraping a single channel."""
    
    channel: str
    videos: int = 0
    comments: int = 0
    bytes_mb: float = 0.0
    duration_sec: float = 0.0
    status: Literal["ok", "failed"] = "ok"
    error: Optional[str] = None
    
    def __repr__(self) -> str:
        if self.status == "failed":
            return f"ChannelStats(channel={self.channel!r}, status='failed', error={self.error!r})"
        return (
            f"ChannelStats(channel={self.channel!r}, videos={self.videos}, "
            f"comments={self.comments}, bytes_mb={self.bytes_mb:.2f}, "
            f"duration_sec={self.duration_sec:.1f})"
        )


@dataclass
class BatchReport:
    """Summary report for batch scraping."""
    
    started_at: str
    finished_at: str
    channels_total: int
    channels_ok: int
    channels_failed: int
    total_videos: int
    total_comments: int
    total_bytes_mb: float
    total_duration_sec: float
    stats: list[dict]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "channels_total": self.channels_total,
            "channels_ok": self.channels_ok,
            "channels_failed": self.channels_failed,
            "total_videos": self.total_videos,
            "total_comments": self.total_comments,
            "total_bytes_mb": round(self.total_bytes_mb, 2),
            "total_duration_sec": round(self.total_duration_sec, 1),
            "stats": self.stats,
        }

