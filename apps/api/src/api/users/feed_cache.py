from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class FeedCacheEntry(Generic[T]):
    feed_id: str
    expires_at: float
    items: list[T]


class InMemoryTTLCache:
    def __init__(self) -> None:
        self._data: dict[str, FeedCacheEntry] = {}

    def get(self, key: str) -> FeedCacheEntry | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.time():
            self._data.pop(key, None)
            return None
        return entry

    def set(self, key: str, entry: FeedCacheEntry) -> None:
        self._data[key] = entry

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


_CACHE = InMemoryTTLCache()
