"""FastAPI server: preview + TTS over the Phase 2/3 pipeline."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from server.pipeline import cleaner, normalizer, splitter
from server.pipeline.cleaner import load_rules
from server.pipeline.llm_reader import LlmReader, current_model_id
from server.pipeline.normalizer import load_yomi
from server.tts import (
    SAMPLE_RATE,
    TTS_LOCK,
    create_voice_prompt,
    generate,
    load_model,
    load_prompt,
    save_prompt,
)

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
    voice: str = "auto"


@app.get("/health")
def health() -> dict[str, object]:
    return {"tts_loaded": _tts is not None, "llm_model": _llm_model_id()}


@app.post("/normalize/preview")
def preview(body: PreviewIn) -> dict[str, object]:
    return {"chunks": build_spoken(body.text, body.use_llm)}


@app.post("/tts")
def tts(body: TtsIn) -> Response:
    chunks = build_spoken(body.text, body.use_llm)
    if not chunks:
        raise HTTPException(400, "本文が空です")
    model = _get_tts()
    prompt = None
    if body.voice != "auto":
        prompt = load_prompt(body.voice)
        if prompt is None:
            raise HTTPException(400, f"voice '{body.voice}' is not registered")
    silence = np.zeros(int(SAMPLE_RATE * 0.2), dtype=np.float32)
    parts = []
    with TTS_LOCK:
        for chunk in chunks:
            parts.append(
                generate(
                    model,
                    chunk["spoken"],
                    speed=body.speed,
                    num_step=16,
                    **({"voice_clone_prompt": prompt} if prompt else {}),
                )
            )
            parts.append(silence)
    buf = io.BytesIO()
    sf.write(buf, np.concatenate(parts), SAMPLE_RATE, format="WAV")
    return Response(content=buf.getvalue(), media_type="audio/wav")


@app.post("/voices/register")
def register_voice(
    ref_audio: UploadFile = File(...),
    ref_text: str = Form(...),
    name: str = Form("narrator"),
) -> dict[str, object]:
    model = _get_tts()
    tmp = Path(f".cache/upload_{name}{Path(ref_audio.filename or 'ref.wav').suffix}")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(ref_audio.file.read())
    path = save_prompt(create_voice_prompt(model, tmp, ref_text), name)
    tmp.unlink(missing_ok=True)
    return {"voice": name, "saved": str(path)}


@app.get("/voices")
def list_voices() -> dict[str, object]:
    from server.tts import VOICES_DIR

    names = sorted(p.stem for p in VOICES_DIR.glob("*.pt")) if VOICES_DIR.exists() else []
    return {"voices": ["auto"] + names}


DICT_FILES = {"replace": Path("dict/user_replace.json"), "yomi": Path("dict/user_yomi.json")}


@app.get("/dict/{name}")
def dict_get(name: str) -> Response:
    if name not in DICT_FILES:
        raise HTTPException(404, "unknown dict")
    return Response(content=DICT_FILES[name].read_text(encoding="utf-8"), media_type="application/json")


@app.put("/dict/{name}")
def dict_put(name: str, body: object = Body(...)) -> dict[str, object]:
    from server.ui import _validate_dict

    if name not in DICT_FILES:
        raise HTTPException(404, "unknown dict")
    try:
        _validate_dict(name, body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    import json as _json

    DICT_FILES[name].write_text(_json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"dict": name, "entries": len(body)}


class LlmModelIn(BaseModel):
    model: str


@app.get("/llm/models")
def llm_models() -> dict[str, object]:
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["llm"]
    return {"active": current_model_id(), "available": cfg.get("available", [cfg["model"]])}


@app.post("/llm/model")
def llm_switch(body: LlmModelIn) -> dict[str, object]:
    from server.ui import switch_model_fn

    try:
        return {"status": switch_model_fn(body.model)}
    except Exception as e:
        raise HTTPException(400, str(e))


import gradio as gr

from server.ui import build_blocks

gr.mount_gradio_app(app, build_blocks(), path="/")
