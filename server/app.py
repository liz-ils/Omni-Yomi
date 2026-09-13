"""FastAPI server: preview + TTS over the Phase 2/3 pipeline."""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf
import yaml
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel

from server.pipeline import cleaner, normalizer, splitter
from server.pipeline.cleaner import load_rules
from server.pipeline.llm_reader import LlmReader
from server.pipeline.normalizer import load_yomi
from server.tts import SAMPLE_RATE, generate, load_model

app = FastAPI(title="Omni-Yomi")

_tts = None
_LLM_MODEL_ID = ""


def _get_tts():
    global _tts
    if _tts is None:
        _tts = load_model()
    return _tts


def _llm_model_id() -> str:
    global _LLM_MODEL_ID
    if not _LLM_MODEL_ID:
        with open("config.yaml", encoding="utf-8") as f:
            _LLM_MODEL_ID = yaml.safe_load(f)["llm"]["model"]
    return _LLM_MODEL_ID


def build_spoken(text: str, use_llm: bool) -> list[dict[str, str]]:
    rules = load_rules("dict/user_replace.json")
    yomi = load_yomi("dict/user_yomi.json")
    cleaned = cleaner.clean(text, rules)
    chunks = splitter.split_chunks(cleaned)
    reader = LlmReader() if use_llm else None
    try:
        out = []
        prev = ""
        for chunk in chunks:
            spoken = normalizer.apply_yomi(
                normalizer.normalize_text(chunk["text"]), yomi
            )
            if reader is not None:
                words = reader.read(chunk["text"], prev).get("words", {})
                spoken = normalizer.apply_yomi(spoken, words)
            prev = chunk["text"]
            out.append(
                {
                    "text": chunk["text"],
                    "kind": chunk["kind"],
                    "lang": normalizer.detect_lang(spoken),
                    "spoken": spoken,
                }
            )
        return out
    finally:
        if reader is not None:
            reader.close()


class PreviewIn(BaseModel):
    text: str
    use_llm: bool = False


class TtsIn(BaseModel):
    text: str
    speed: float = 1.0
    use_llm: bool = False


@app.get("/")
def index() -> dict[str, object]:
    return {"service": "Omni-Yomi", "endpoints": ["/health", "/normalize/preview", "/tts"]}


@app.get("/health")
def health() -> dict[str, object]:
    return {"tts_loaded": _tts is not None, "llm_model": _llm_model_id()}


@app.post("/normalize/preview")
def preview(body: PreviewIn) -> dict[str, object]:
    return {"chunks": build_spoken(body.text, body.use_llm)}


@app.post("/tts")
def tts(body: TtsIn) -> Response:
    model = _get_tts()
    silence = np.zeros(int(SAMPLE_RATE * 0.2), dtype=np.float32)
    parts = []
    for chunk in build_spoken(body.text, body.use_llm):
        parts.append(generate(model, chunk["spoken"], speed=body.speed, num_step=16))
        parts.append(silence)
    buf = io.BytesIO()
    sf.write(buf, np.concatenate(parts), SAMPLE_RATE, format="WAV")
    return Response(content=buf.getvalue(), media_type="audio/wav")
