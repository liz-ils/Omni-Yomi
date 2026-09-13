"""Split into chunks with dialogue/narration tags."""

from __future__ import annotations

import re

_SENTENCE = re.compile(r"[^。！？!?]+[。！？!?」]*|[^。！？!?]+$")


def _kind(sentence: str) -> str:
    s = sentence.strip()
    if s.startswith("「") or s.startswith("『"):
        return "dialogue"
    return "narration"


def split_sentences(text: str) -> list[dict[str, str]]:
    out = []
    for m in _SENTENCE.finditer(text):
        s = m.group(0).strip()
        if s:
            out.append({"text": s, "kind": _kind(s)})
    return out


def split_chunks(text: str, max_len: int = 400) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    buf = ""
    buf_kind = "narration"
    for sent in split_sentences(text):
        if buf and (len(buf) + len(sent["text"]) > max_len or sent["kind"] != buf_kind):
            chunks.append({"text": buf, "kind": buf_kind})
            buf = ""
        if not buf:
            buf_kind = sent["kind"]
        buf += sent["text"]
    if buf:
        chunks.append({"text": buf, "kind": buf_kind})
    return chunks
