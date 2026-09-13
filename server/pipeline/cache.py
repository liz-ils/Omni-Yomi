"""File-backed cache: text_hash -> value."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class JsonCache:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._data: dict[str, object] | None = None

    def _load(self) -> dict[str, object]:
        if self._data is None:
            if self.path.exists():
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            else:
                self._data = {}
        return self._data

    def get(self, text: str) -> object | None:
        return self._load().get(key(text))

    def set(self, text: str, value: object) -> None:
        data = self._load()
        data[key(text)] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
