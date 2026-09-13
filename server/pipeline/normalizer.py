"""Normalize: NFKC, user yomi, lang detect, fugashi readings."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

_ASCII_LETTER = re.compile(r"[A-Za-z]")

_tagger = None


def _get_tagger():
    global _tagger
    if _tagger is None:
        from fugashi import Tagger

        _tagger = Tagger()
    return _tagger


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n +", "\n", text)
    return text.strip()


def detect_lang(text: str) -> str:
    """Sentence-level ja/en detection for language_id routing (MVP heuristic)."""
    letters = _ASCII_LETTER.findall(text)
    if text and len(letters) / max(len(text), 1) > 0.5:
        return "en"
    return "ja"


def load_yomi(path: str | Path) -> dict[str, str]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def apply_yomi(text: str, yomi: dict[str, str]) -> str:
    for surface in sorted(yomi, key=len, reverse=True):
        text = text.replace(surface, yomi[surface])
    return text


def readings(text: str) -> list[tuple[str, str]]:
    """Return (surface, katakana pronunciation) pairs via fugashi."""
    return [(w.surface, str(w.feature.pron or w.surface)) for w in _get_tagger()(text)]
