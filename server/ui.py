"""Gradio control page (OmniVoice-demo style). Mounted at / by server.app."""

import json
from pathlib import Path

import gradio as gr
import numpy as np
import soundfile as sf
import yaml

from server.app import _get_tts, build_spoken
from server.pipeline.llm_reader import current_model_id, set_current_model
from server.tts import (
    SAMPLE_RATE,
    VOICES_DIR,
    create_voice_prompt,
    generate,
    load_prompt,
    save_prompt,
)

DICT_FILES = {"replace": Path("dict/user_replace.json"), "yomi": Path("dict/user_yomi.json")}
OUT_WAV = Path(".cache/ui_out.wav")


def _voices() -> list[str]:
    names = sorted(p.stem for p in VOICES_DIR.glob("*.pt")) if VOICES_DIR.exists() else []
    return ["auto"] + names


def _models() -> list[str]:
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["llm"]
    return cfg.get("available", [cfg["model"]])


def preview_fn(text: str, use_llm: bool) -> str:
    return "\n".join(
        f"[{c['kind']}/{c['lang']}] {c['spoken']}"
        for c in build_spoken(text, use_llm)
    )


def tts_fn(text: str, speed: float, use_llm: bool, voice: str) -> str:
    chunks = build_spoken(text, use_llm)
    if not chunks:
        raise gr.Error("本文が空です")
    model = _get_tts()
    prompt = None
    if voice != "auto":
        prompt = load_prompt(voice)
        if prompt is None:
            raise gr.Error(f"voice '{voice}' is not registered")
    silence = np.zeros(int(SAMPLE_RATE * 0.2), dtype=np.float32)
    parts = []
    for chunk in chunks:
        parts.append(
            generate(
                model,
                chunk["spoken"],
                speed=speed,
                num_step=16,
                **({"voice_clone_prompt": prompt} if prompt else {}),
            )
        )
        parts.append(silence)
    OUT_WAV.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(OUT_WAV), np.concatenate(parts), SAMPLE_RATE)
    return str(OUT_WAV)


def register_fn(ref_audio: str | None, ref_text: str):
    if not ref_audio:
        raise gr.Error("reference audio is required")
    if not ref_text.strip():
        raise gr.Error("ref_text is required")
    path = save_prompt(create_voice_prompt(_get_tts(), ref_audio, ref_text.strip()))
    return f"registered: {path}", gr.update(choices=_voices(), value="narrator")


def switch_model_fn(model_id: str) -> str:
    if model_id not in _models():
        raise gr.Error(f"model '{model_id}' is not in available list")
    set_current_model(model_id)
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["llm"]["model"] = model_id
    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True)
    return f"active LLM: {model_id}"


def dict_get_fn(name: str) -> str:
    return DICT_FILES[name].read_text(encoding="utf-8")


def _validate_dict(name: str, data: object) -> None:
    if name == "replace":
        if not isinstance(data, list) or any(
            not isinstance(i, dict) or set(i) != {"pattern", "replace"} for i in data
        ):
            raise ValueError('replace must be [{"pattern": ..., "replace": ...}]')
    else:
        if not isinstance(data, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in data.items()
        ):
            raise ValueError('yomi must be {"surface": "reading"}')


def dict_save_fn(name: str, raw: str) -> str:
    try:
        data = json.loads(raw)
        _validate_dict(name, data)
    except (json.JSONDecodeError, ValueError) as e:
        raise gr.Error(f"invalid {name}: {e}")
    DICT_FILES[name].write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"saved {name} ({len(data)} entries)"


def build_blocks() -> gr.Blocks:
    with gr.Blocks(title="Omni-Yomi") as demo:
        gr.Markdown("# Omni-Yomi")
        with gr.Row():
            model = gr.Dropdown(_models(), value=current_model_id(), label="LLM")
            model_status = gr.Textbox(label="status", interactive=False)
        model.change(switch_model_fn, model, model_status)
        text = gr.Textbox(lines=10, label="本文")
        with gr.Row():
            speed = gr.Slider(0.5, 1.5, value=1.0, step=0.1, label="速度")
            use_llm = gr.Checkbox(label="LLM読み付け")
            voice = gr.Dropdown(_voices(), value="auto", label="声")
        with gr.Row():
            preview_btn = gr.Button("プレビュー")
            speak_btn = gr.Button("読み上げ", variant="primary")
        preview_out = gr.Textbox(label="プレビュー", interactive=False)
        audio_out = gr.Audio(label="音声")
        preview_btn.click(preview_fn, [text, use_llm], preview_out)
        speak_btn.click(tts_fn, [text, speed, use_llm, voice], audio_out)
        with gr.Accordion("声の登録 (ボイスクローン)", open=False):
            with gr.Row():
                ref_audio = gr.Audio(type="filepath", label="リファレンス音声 (3-10秒)")
                ref_text = gr.Textbox(label="書き起こし")
            register_btn = gr.Button("声を登録")
            register_out = gr.Textbox(label="status", interactive=False)
            register_btn.click(register_fn, [ref_audio, ref_text], [register_out, voice])
        with gr.Accordion("辞書 (JSON)", open=False):
            for name in ("replace", "yomi"):
                editor = gr.Textbox(
                    value=dict_get_fn(name), lines=6, label=f"dict/{name}.json"
                )
                save_btn = gr.Button(f"{name} を保存")
                save_out = gr.Textbox(label="status", interactive=False)
                save_btn.click(
                    lambda raw, n=name: dict_save_fn(n, raw), editor, save_out
                )
    return demo
