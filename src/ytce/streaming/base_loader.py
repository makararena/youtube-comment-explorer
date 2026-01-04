from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Mapping


class StreamingLoader(ABC):
    """Base interface for streaming loaders."""

    @abstractmethod
    def send_events(self, events: Iterable[Mapping[str, Any]]) -> int:
        """Send events and return the count successfully sent."""

    def close(self) -> None:
        """Close any underlying resources."""
        return None
