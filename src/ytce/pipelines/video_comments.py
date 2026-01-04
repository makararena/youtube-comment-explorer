from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Optional

from ytce.__version__ import __version__
from ytce.storage.state import CommentState, load_comment_state, save_comment_state
from ytce.storage.writers import write_csv, write_jsonl, write_parquet
from ytce.streaming import AzureEventHubsLoader, LocalFileStreamingLoader, StreamingLoader
from ytce.utils.progress import CommentProgressTracker, print_error, print_step, print_success, print_warning
from ytce.youtube.comments import SORT_BY_POPULAR, SORT_BY_RECENT, YoutubeCommentDownloader


DEFAULT_STREAMING_CONFIG = {
    "enabled": False,
    "provider": "azure_event_hubs",
    "poll_interval_sec": 30,
    "event_hubs": {
        "enabled": False,
        "connection_string": "",
        "event_hub_name": "",
        "max_batch_size": 200,
        "flush_interval_sec": 1.0,
    },
    "local": {
        "path": "",
    },
}


@dataclass
class PollStats:
    fetched: int
    new: int
    updated: int
    streamed: int
    duration_sec: float
    updated_details: list[dict[str, Any]] = field(default_factory=list)  # List of {cid, changed_fields}


def run(
    *,
    video_id: str,
    output: str,
    sort: str,
    limit: Optional[int],
    language: Optional[str],
    format: str = "jsonl",
    streaming: Optional[Mapping[str, Any]] = None,
) -> None:
    streaming_config = _merge_streaming_config(streaming or {})
    loader = _init_streaming_loader(streaming_config, output)
    streaming_requested = bool(streaming_config.get("enabled"))
    streaming_active = streaming_requested and loader is not None
    poll_interval_sec = streaming_config.get("poll_interval_sec") if streaming_active else None

    try:
        while True:
            stats = _poll_once(
                video_id=video_id,
                output=output,
                sort=sort,
                limit=limit,
                language=language,
                format=format,
                loader=loader,
                streaming_active=streaming_active,
                streaming_requested=streaming_requested,
            )
            _print_poll_stats(video_id, stats)

            if not streaming_active or not poll_interval_sec or poll_interval_sec <= 0:
                break

            time.sleep(poll_interval_sec)
    finally:
        if loader:
            loader.close()


def _poll_once(
    *,
    video_id: str,
    output: str,
    sort: str,
    limit: Optional[int],
    language: Optional[str],
    format: str,
    loader: Optional[StreamingLoader],
    streaming_active: bool,
    streaming_requested: bool,
) -> PollStats:
    poll_start = time.time()
    print_step(f"Fetching comments for video: {video_id}")

    downloader = YoutubeCommentDownloader()
    sort_by = SORT_BY_RECENT if sort == "recent" else SORT_BY_POPULAR

    gen = downloader.get_comments(video_id, sort_by=sort_by, language=language, sleep=0.1)
    scraped_at_dt = datetime.now(timezone.utc)
    scraped_at = scraped_at_dt.isoformat()

    # Extract total comment count from generator (first item might be metadata)
    total_count = None
    first_item = next(gen, None)
    if first_item and isinstance(first_item, dict) and "_total_count" in first_item:
        total_count = first_item["_total_count"]
        expected_total = limit if limit is not None else total_count
    else:
        expected_total = limit
        if first_item:
            def _prepend_item(gen, item):
                yield item
                yield from gen
            gen = _prepend_item(gen, first_item)

    progress_tracker = CommentProgressTracker(video_id, 1, 1, expected_total=expected_total)

    state_path, delta_path = _state_and_delta_paths(output)
    state = load_comment_state(state_path)
    new_comments = []
    fetched_count = 0
    updated_count = 0
    updated_details = []
    state_comments = state.comments

    def limited() -> Iterable[Mapping[str, Any]]:
        nonlocal gen, fetched_count, updated_count, updated_details
        count = 0
        for c in gen:
            if isinstance(c, dict) and "_total_count" in c:
                continue
            comment_data = dict(c) if isinstance(c, dict) else c.__dict__
            comment_data["scraped_at"] = scraped_at
            comment_data["time_raw"] = comment_data.get("time")
            comment_data["source"] = f"ytce/{__version__}"

            fetched_count += 1

            cid = comment_data.get("cid")
            if cid:
                previous = state_comments.get(cid)
                if is_new_comment(cid, state):
                    approx_published_at = parse_relative_time(comment_data.get("time"), scraped_at_dt)
                    comment_data["first_seen_at"] = scraped_at
                    comment_data["approx_published_at"] = (
                        approx_published_at.isoformat() if approx_published_at else None
                    )
                    state_comments[cid] = _normalize_comment(comment_data)
                    new_comments.append(comment_data)
                else:
                    comment_data["first_seen_at"] = previous.get("first_seen_at")
                    comment_data["approx_published_at"] = previous.get("approx_published_at")
                    normalized = _normalize_comment(comment_data)
                    normalized_prev = _normalize_for_compare(previous)
                    normalized_curr = _normalize_for_compare(normalized)
                    if normalized_curr != normalized_prev:
                        updated_count += 1
                        changed_fields = _get_changed_fields(normalized_prev, normalized_curr)
                        updated_details.append({
                            "cid": cid,
                            "changed_fields": changed_fields
                        })
                    state_comments[cid] = normalized

            yield comment_data
            count += 1
            if limit is not None and count >= limit:
                break

    if format == "csv":
        wrote = write_csv(output, limited(), progress_callback=progress_tracker.update)
    elif format == "parquet":
        wrote = write_parquet(output, limited(), progress_callback=progress_tracker.update)
    else:
        wrote = write_jsonl(output, limited(), progress_callback=progress_tracker.update)

    progress_tracker.finish(wrote)
    print_success(f"Saved to {output}")

    _write_delta(delta_path, new_comments, format)

    streamed_count = 0
    if streaming_active and loader and new_comments:
        try:
            streamed_count = loader.send_events(new_comments)
            if streamed_count > 0:
                print_success(f"Streamed {streamed_count} event(s) to Azure Event Hubs")
        except Exception as exc:
            print_error(f"Failed to stream events: {exc}")

    state_to_save = CommentState(last_poll_at=scraped_at, comments=state_comments)
    try:
        save_comment_state(state_path, state_to_save)
    except Exception as exc:
        print_warning(f"Failed to save state file {state_path}: {exc}")

    duration = time.time() - poll_start
    return PollStats(
        fetched=fetched_count,
        new=len(new_comments),
        updated=updated_count,
        streamed=streamed_count,
        duration_sec=duration,
        updated_details=updated_details,
    )


def _merge_streaming_config(config: Mapping[str, Any]) -> dict[str, Any]:
    merged = {
        "enabled": DEFAULT_STREAMING_CONFIG["enabled"],
        "provider": DEFAULT_STREAMING_CONFIG["provider"],
        "poll_interval_sec": DEFAULT_STREAMING_CONFIG["poll_interval_sec"],
        "event_hubs": DEFAULT_STREAMING_CONFIG["event_hubs"].copy(),
        "local": DEFAULT_STREAMING_CONFIG["local"].copy(),
    }
    for key, value in config.items():
        if key not in ("event_hubs", "local"):
            merged[key] = value
    event_hubs = config.get("event_hubs", {})
    if isinstance(event_hubs, Mapping):
        merged["event_hubs"].update(event_hubs)
    local_config = config.get("local", {})
    if isinstance(local_config, Mapping):
        merged["local"].update(local_config)
    return merged


def _init_streaming_loader(streaming_config: Mapping[str, Any], output: str) -> Optional[StreamingLoader]:
    if not streaming_config.get("enabled"):
        return None

    provider = streaming_config.get("provider")
    if provider == "local":
        local_config = streaming_config.get("local", {})
        stream_path = local_config.get("path") if isinstance(local_config, Mapping) else None
        stream_path = stream_path or _local_stream_path(output)
        try:
            return LocalFileStreamingLoader(stream_path)
        except Exception as exc:
            print_warning(f"Failed to initialize local streaming loader: {exc}")
            return None

    if provider != "azure_event_hubs":
        print_warning(f"Streaming provider '{provider}' is not supported.")
        return None

    event_hubs = streaming_config.get("event_hubs", {})
    if not event_hubs.get("enabled"):
        print_warning("Event Hubs streaming is disabled in config.")
        return None

    connection_string = event_hubs.get("connection_string")
    if not connection_string:
        print_warning("Event Hubs connection string is missing.")
        return None

    try:
        loader = AzureEventHubsLoader(
            connection_string=connection_string,
            event_hub_name=event_hubs.get("event_hub_name"),
            max_batch_size=event_hubs.get("max_batch_size", 200),
            flush_interval_sec=event_hubs.get("flush_interval_sec", 1.0),
        )
        event_hub_name = event_hubs.get("event_hub_name") or "default"
        print_success(f"Connected to Azure Event Hubs: {event_hub_name}")
        return loader
    except Exception as exc:
        print_warning(f"Failed to initialize Event Hubs loader: {exc}")
        return None


def _state_and_delta_paths(output: str) -> tuple[str, str]:
    base, ext = os.path.splitext(output)
    if not ext:
        ext = ".jsonl"
    return f"{base}.state.json", f"{base}.delta{ext}"


def _local_stream_path(output: str) -> str:
    base, _ = os.path.splitext(output)
    return f"{base}.stream.jsonl"


def _write_delta(path: str, items: list[Mapping[str, Any]], format: str) -> None:
    if format == "csv":
        if items:
            write_csv(path, items)
        else:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as _:
                pass
        return
    if format == "parquet":
        write_parquet(path, items)
        return
    write_jsonl(path, items)


def _normalize_comment(comment: Mapping[str, Any]) -> dict[str, Any]:
    return dict(comment)


def is_new_comment(cid: str, state: CommentState) -> bool:
    return cid not in state.comments


def _normalize_for_compare(comment: Mapping[str, Any]) -> dict[str, Any]:
    ignore_keys = {"scraped_at", "time_raw", "time", "approx_published_at", "first_seen_at"}
    return {k: v for k, v in comment.items() if k not in ignore_keys}


def _get_changed_fields(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """Return list of field names that changed between previous and current comment."""
    changed = []
    all_keys = set(previous.keys()) | set(current.keys())
    for key in all_keys:
        prev_val = previous.get(key)
        curr_val = current.get(key)
        if prev_val != curr_val:
            changed.append(key)
    return sorted(changed)


def parse_relative_time(time_str: Optional[str], now: datetime) -> Optional[datetime]:
    if not time_str:
        return None

    try:
        value, unit, _ = time_str.split()
        value = int(value)
        unit = unit.lower()

        if "minute" in unit:
            return now - timedelta(minutes=value)
        if "hour" in unit:
            return now - timedelta(hours=value)
        if "day" in unit:
            return now - timedelta(days=value)
    except Exception:
        return None

    return None


def _print_poll_stats(video_id: str, stats: PollStats) -> None:
    print("Poll finished")
    print(f"Video ID: {video_id}")
    print(f"Fetched comments: {stats.fetched}")
    print(f"New comments: {stats.new}")
    print(f"Updated comments: {stats.updated}")
    print(f"Streamed events: {stats.streamed}")
    print(f"Poll duration: {stats.duration_sec:.2f}s")
    
    # Print update details if available
    if stats.updated_details:
        print(f"\nUpdate details:")
        for detail in stats.updated_details:
            cid_short = detail["cid"][:12] + "..." if len(detail["cid"]) > 12 else detail["cid"]
            fields = ", ".join(detail["changed_fields"])
            print(f"  {cid_short}: {fields}")
