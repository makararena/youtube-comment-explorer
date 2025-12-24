from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ytce.__version__ import __version__
from ytce.storage.writers import write_json, write_videos_csv
from ytce.utils.progress import format_number, print_step, print_success
from ytce.youtube.channel_videos import YoutubeChannelVideosScraper


def run(*, channel_id: str, output: str, max_videos: Optional[int], debug: bool, format: str = "json") -> None:
    print_step(f"Fetching channel: {channel_id}")
    scraper = YoutubeChannelVideosScraper(debug=debug)
    videos = scraper.get_all_videos(channel_id, max_videos=max_videos, show_progress=False)
    
    # Add metadata
    data = {
        "channel_id": channel_id,
        "total_videos": len(videos),
        "videos": videos,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source": f"ytce/{__version__}",
    }
    
    if format == "csv":
        write_videos_csv(output, data)
    else:
        write_json(output, data)
    print_success(f"Found {format_number(len(videos))} videos")
    print_success(f"Saved to {output}")
