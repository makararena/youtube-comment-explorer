from __future__ import annotations

import csv
import io
import json
import os
from typing import Any, Dict, Iterable, List, Optional


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_json(path: str, payload: Any) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_jsonl(path: str, items: Iterable[Dict[str, Any]]) -> int:
    ensure_dir(os.path.dirname(path) or ".")
    count = 0
    with io.open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_csv(path: str, items: Iterable[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> int:
    """
    Write items to a CSV file.
    
    Args:
        path: Output file path
        items: Iterable of dictionaries to write
        fieldnames: Optional list of field names (if None, inferred from first item)
    
    Returns:
        Number of rows written (excluding header)
    """
    ensure_dir(os.path.dirname(path) or ".")
    count = 0
    
    # Convert generator to list to get fieldnames if needed
    items_list = list(items)
    
    if not items_list:
        # Create empty CSV with headers if fieldnames provided
        if fieldnames:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
        return 0
    
    # Determine fieldnames
    if fieldnames is None:
        # Get all unique keys from all items
        all_keys = set()
        for item in items_list:
            all_keys.update(item.keys())
        fieldnames = sorted(all_keys)
    
    # Write CSV
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        
        for item in items_list:
            # Convert all values to strings, handling None and booleans
            row = {}
            for key in fieldnames:
                value = item.get(key, "")
                if value is None:
                    row[key] = ""
                elif isinstance(value, bool):
                    row[key] = str(value).lower()
                elif isinstance(value, (dict, list)):
                    # Convert complex types to JSON string
                    row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    row[key] = str(value)
            writer.writerow(row)
            count += 1
    
    return count


def write_videos_csv(path: str, videos_data: Dict[str, Any]) -> int:
    """
    Write videos metadata to CSV format.
    
    Args:
        path: Output file path
        videos_data: Dictionary with 'videos' key containing list of video dicts
    
    Returns:
        Number of videos written
    """
    ensure_dir(os.path.dirname(path) or ".")
    videos = videos_data.get("videos", [])
    
    if not videos:
        # Create empty CSV with headers
        fieldnames = [
            "video_id", "title", "url", "order", "channel_id",
            "view_count", "view_count_raw", "length", "thumbnail_url"
        ]
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        return 0
    
    # Determine fieldnames from first video
    fieldnames = list(videos[0].keys())
    
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        
        for video in videos:
            row = {}
            for key in fieldnames:
                value = video.get(key, "")
                if value is None:
                    row[key] = ""
                elif isinstance(value, bool):
                    row[key] = str(value).lower()
                elif isinstance(value, (dict, list)):
                    row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    row[key] = str(value)
            writer.writerow(row)
    
    return len(videos)
