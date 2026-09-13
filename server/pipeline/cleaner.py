"""Cleaning: presets + user regex replacements."""

from __future__ import annotations

import json
import re
from pathlib import Path

# (pattern, replacement) applied in order before user rules.
PRESETS: list[tuple[str, str]] = [
    (r"[─―—]{2,}", ""),  # 長いダッシュは読み飛ばし
    (r"[♪♫※＊*☆★◎○●◇◆□■]", ""),  # 装飾記号は除去
    (r"\r\n", "\n"),
    (r"\n{3,}", "\n\n"),
]

_COMPILED_PRESETS = [(re.compile(p), r) for p, r in PRESETS]


def load_rules(path: str | Path) -> list[tuple[re.Pattern[str], str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [(re.compile(item["pattern"]), item["replace"]) for item in data]


def clean(text: str, rules: list[tuple[re.Pattern[str], str]] = []) -> str:
    for pattern, replacement in _COMPILED_PRESETS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in rules:
        text = pattern.sub(replacement, text)
    return text.strip()
