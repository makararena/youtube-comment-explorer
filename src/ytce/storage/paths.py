from __future__ import annotations

import os

from ytce.utils.helpers import sanitize_name


def channel_videos_path(channel_id: str, base_dir: str = "data") -> str:
    return os.path.join(base_dir, sanitize_name(channel_id), "videos.json")


def video_comments_path(video_id: str, base_dir: str = "data", format: str = "jsonl") -> str:
    if format == "csv":
        ext = "csv"
    elif format == "parquet":
        ext = "parquet"
    else:
        ext = "jsonl"
    return os.path.join(base_dir, sanitize_name(video_id), f"comments.{ext}")


def channel_output_dir(channel_id: str, base_dir: str = "data") -> str:
    return os.path.join(base_dir, sanitize_name(channel_id))


def channel_comments_dir(out_dir: str) -> str:
    return os.path.join(out_dir, "comments")


def video_comments_filename(order: int, video_id: str, format: str = "jsonl") -> str:
    if format == "csv":
        ext = "csv"
    elif format == "parquet":
        ext = "parquet"
    else:
        ext = "jsonl"
    return f"{order:04d}_{video_id}.{ext}"


def channel_videos_path_with_format(channel_id: str, base_dir: str = "data", format: str = "json") -> str:
    """Get path for channel videos file with specified format."""
    if format == "csv":
        ext = "csv"
    elif format == "parquet":
        ext = "parquet"
    else:
        ext = "json"
    return os.path.join(base_dir, sanitize_name(channel_id), f"videos.{ext}")
