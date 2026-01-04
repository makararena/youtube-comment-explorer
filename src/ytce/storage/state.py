from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ytce.storage.writers import ensure_dir
from ytce.utils.progress import print_warning


@dataclass
class CommentState:
    last_poll_at: Optional[str]
    comments: Dict[str, Dict[str, Any]]


def load_comment_state(path: str) -> CommentState:
    if not os.path.exists(path):
        return CommentState(last_poll_at=None, comments={})

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception as exc:
        print_warning(f"Failed to load state file {path}: {exc}")
        return CommentState(last_poll_at=None, comments={})

    if not isinstance(data, dict):
        return CommentState(last_poll_at=None, comments={})

    last_poll_at = data.get("last_poll_at")
    comments = data.get("comments")
    if not isinstance(comments, dict):
        comments = {}

    return CommentState(last_poll_at=last_poll_at, comments=comments)


def save_comment_state(path: str, state: CommentState) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    payload = {"last_poll_at": state.last_poll_at, "comments": state.comments}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
