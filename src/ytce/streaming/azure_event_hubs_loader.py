from __future__ import annotations

import json
import time
from typing import Any, Iterable, Mapping, Optional

from ytce.streaming.base_loader import StreamingLoader
from ytce.utils.progress import print_error, print_success

try:
    from azure.eventhub import EventData, EventHubProducerClient
except ImportError:  # pragma: no cover - optional dependency
    EventData = None
    EventHubProducerClient = None


class AzureEventHubsLoader(StreamingLoader):
    """Azure Event Hubs streaming loader with micro-batching."""

    def __init__(
        self,
        *,
        connection_string: str,
        event_hub_name: Optional[str],
        max_batch_size: int = 200,
        flush_interval_sec: float = 1.0,
    ) -> None:
        if EventHubProducerClient is None or EventData is None:
            raise ImportError(
                "azure-eventhub is required for Azure Event Hubs streaming. "
                "Install it with: pip install azure-eventhub"
            )

        self._producer = EventHubProducerClient.from_connection_string(
            conn_str=connection_string,
            eventhub_name=event_hub_name or None,
        )
        self._max_batch_size = _clamp_batch_size(max_batch_size)
        self._flush_interval_sec = max(0.1, float(flush_interval_sec))

    def send_events(self, events: Iterable[Mapping[str, Any]]) -> int:
        sent = 0
        batch = self._producer.create_batch()
        batch_count = 0
        last_flush = time.monotonic()

        for event in events:
            payload = json.dumps(event, ensure_ascii=False)
            event_data = EventData(payload)
            properties = {}
            cid = event.get("cid")
            if cid:
                properties["cid"] = cid
            first_seen_at = event.get("first_seen_at")
            if first_seen_at:
                properties["first_seen_at"] = first_seen_at
            if properties:
                event_data.properties = properties
            try:
                batch.add(event_data)
            except ValueError:
                if batch_count > 0:
                    self._producer.send_batch(batch)
                    sent += batch_count
                    print_success(f"Sent batch of {batch_count} event(s) to Azure Event Hubs (batch full)")
                batch = self._producer.create_batch()
                batch_count = 0
                try:
                    batch.add(event_data)
                except ValueError:
                    print_error("Event too large to send, skipping.")
                    continue
            else:
                batch_count += 1

            now = time.monotonic()
            if batch_count >= self._max_batch_size or (now - last_flush) >= self._flush_interval_sec:
                self._producer.send_batch(batch)
                sent += batch_count
                print_success(f"Sent batch of {batch_count} event(s) to Azure Event Hubs")
                batch = self._producer.create_batch()
                batch_count = 0
                last_flush = now

        if batch_count > 0:
            self._producer.send_batch(batch)
            sent += batch_count
            print_success(f"Sent final batch of {batch_count} event(s) to Azure Event Hubs")

        return sent

    def close(self) -> None:
        self._producer.close()


def _clamp_batch_size(value: int) -> int:
    if value < 100:
        return 100
    if value > 500:
        return 500
    return value
