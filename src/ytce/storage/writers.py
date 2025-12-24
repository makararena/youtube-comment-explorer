from __future__ import annotations

import csv
import io
import json
import os
from typing import Any, Callable, Dict, Iterable, List, Optional


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_json(path: str, payload: Any) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_jsonl(
    path: str, 
    items: Iterable[Dict[str, Any]], 
    progress_callback: Optional[Callable[[int], None]] = None,
) -> int:
    ensure_dir(os.path.dirname(path) or ".")
    count = 0
    with io.open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
            if progress_callback:
                progress_callback(count)
    return count


def write_csv(
    path: str, 
    items: Iterable[Dict[str, Any]], 
    fieldnames: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> int:
    """
    Write items to a CSV file in streaming fashion (writes as items come in).
    
    Args:
        path: Output file path
        items: Iterable of dictionaries to write
        fieldnames: Optional list of field names (if None, inferred from first item)
        progress_callback: Optional callback function(count) called after each item is written
    
    Returns:
        Number of rows written (excluding header)
    """
    ensure_dir(os.path.dirname(path) or ".")
    count = 0
    
    # Peek at first item to determine fieldnames if needed
    items_iter = iter(items)
    first_item = None
    
    try:
        first_item = next(items_iter)
    except StopIteration:
        # Empty iterator - create empty CSV with headers if fieldnames provided
        if fieldnames:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
        return 0
    
    # Determine fieldnames
    if fieldnames is None:
        # Get all keys from first item, then collect any additional keys from remaining items
        all_keys = set(first_item.keys())
        # We'll write the first item, then check remaining items for any new keys
        # For now, use keys from first item - additional keys will be handled by extrasaction
        fieldnames = sorted(all_keys)
    
    # Write CSV in streaming fashion
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        
        # Write first item
        row = _convert_item_to_row(first_item, fieldnames)
        writer.writerow(row)
        count += 1
        if progress_callback:
            progress_callback(count)
        
        # Write remaining items as they come in
        for item in items_iter:
            row = _convert_item_to_row(item, fieldnames)
            writer.writerow(row)
            count += 1
            if progress_callback:
                progress_callback(count)
    
    return count


def _convert_item_to_row(item: Dict[str, Any], fieldnames: List[str]) -> Dict[str, str]:
    """Convert a dictionary item to a CSV row with proper type conversion."""
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
    return row


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
            "video_id", "title", "title_length", "url", "order", "channel_id",
            "view_count", "view_count_raw", "length", "length_minutes", "thumbnail_url"
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
