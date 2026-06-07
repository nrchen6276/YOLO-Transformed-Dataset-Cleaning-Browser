from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ThumbnailKey:
    path: str
    size: int
    mtime_ns: int


class ThumbnailCache:
    def __init__(self, max_items: int = 80) -> None:
        self.max_items = max_items
        self.cache: OrderedDict[ThumbnailKey, Any] = OrderedDict()

    def key_for(self, path: Path) -> ThumbnailKey:
        stat = path.stat()
        return ThumbnailKey(str(path), stat.st_size, stat.st_mtime_ns)

    def get(self, path: Path) -> Any | None:
        key = self.key_for(path)
        value = self.cache.get(key)
        if value is not None:
            self.cache.move_to_end(key)
        return value

    def put(self, path: Path, value: Any) -> None:
        key = self.key_for(path)
        self.cache[key] = value
        self.cache.move_to_end(key)
        while len(self.cache) > self.max_items:
            self.cache.popitem(last=False)
