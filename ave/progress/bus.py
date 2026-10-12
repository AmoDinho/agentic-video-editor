"""Progress events from workers to the API.

Redis is used when REDIS_URL is set. Tests and a single process use an
in-memory bus with the same publish and listen shape. The API is responsible
for holding the stream to at most 4 events a second.
"""

from __future__ import annotations

import json
import os
import threading
from collections import defaultdict
from collections.abc import Iterator
from typing import Any


class MemoryBus:
    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._cond = threading.Condition()

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        with self._cond:
            self._events[channel].append(payload)
            self._cond.notify_all()

    def listen(self, channel: str, *, after: int = 0, timeout: float = 0.25) -> list[dict[str, Any]]:
        with self._cond:
            current = self._events[channel]
            if after < len(current):
                return list(current[after:])
            self._cond.wait(timeout=timeout)
            return list(self._events[channel][after:])


BUS = MemoryBus()


def publish(channel: str, payload: dict[str, Any]) -> None:
    url = os.environ.get("REDIS_URL", "")
    if url:
        _redis_publish(url, channel, payload)
        return
    BUS.publish(channel, payload)


def listen(channel: str, *, after: int = 0, timeout: float = 0.25) -> list[dict[str, Any]]:
    url = os.environ.get("REDIS_URL", "")
    if url:
        return _redis_listen(url, channel, timeout=timeout)
    return BUS.listen(channel, after=after, timeout=timeout)


def _redis_publish(url: str, channel: str, payload: dict[str, Any]) -> None:
    import redis

    redis.Redis.from_url(url).publish(channel, json.dumps(payload))


def _redis_listen(url: str, channel: str, *, timeout: float) -> Iterator[dict[str, Any]] | list[dict[str, Any]]:
    import redis

    client = redis.Redis.from_url(url)
    pubsub = client.pubsub()
    pubsub.subscribe(channel)
    message = pubsub.get_message(timeout=timeout)
    pubsub.close()
    if not message or message.get("type") != "message":
        return []
    data = message["data"]
    if isinstance(data, bytes):
        data = data.decode()
    return [json.loads(data)]
