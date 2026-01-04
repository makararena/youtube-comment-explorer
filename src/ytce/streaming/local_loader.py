from __future__ import annotations

import json
import os
from typing import Any, Iterable, Mapping

from ytce.storage.writers import ensure_dir
from ytce.streaming.base_loader import StreamingLoader


class LocalFileStreamingLoader(StreamingLoader):
    """Write streamed events to a local JSONL file."""

    def __init__(self, path: str) -> None:
        self._path = path
        ensure_dir(os.path.dirname(path) or ".")

    def send_events(self, events: Iterable[Mapping[str, Any]]) -> int:
        count = 0
        with open(self._path, "a", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
                count += 1
        return count
