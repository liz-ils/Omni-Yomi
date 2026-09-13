"""LLM reader: constrained yomi generation with a swappable model.

Default: LiquidAI/LFM2.5-1.2B-JP-202606 (transformers, BF16, CUDA).
Switch via config.yaml `llm.model` (e.g. openbmb/MiniCPM5-2B).

Load the model only while normalizing, then close it before TTS
so VRAM is not shared with OmniVoice.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import torch
import yaml
from transformers import AutoModelForCausalLM, AutoTokenizer

from server.pipeline.cache import JsonCache

SYSTEM = (
    "対象文の中から読みが曖昧な語だけ抜き出し、読みを付けよ。"
    "読みは全角カタカナで書け。読みが自明な語（彼、残り、叫ぶ、走る等）は出すな。"
    "出力は次のJSONを1行だけ。説明・言い換えは禁止。"
    '{"words": {"表記": "カタカナ読み"}}'
    "該当なしは {\"words\": {}}。"
    '例: 対象: 明日、明日香と日本橋で会った。 前文: 舞台は大阪だ。'
    '出力: {"words": {"明日": "アシタ", "明日香": "アスカ", "日本橋": "ニホンバシ"}}'
    '例: 対象: 彼は走って逃げた。 出力: {"words": {}}'
)

_JSON = re.compile(r"\{.*\}", re.DOTALL)
_KATAKANA = re.compile(r"[ァ-ヶー・]+")


def _to_katakana(s: str) -> str:
    return "".join(
        chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s.strip()
    )


def sanitize_words(text: str, words: object) -> dict[str, str]:
    """Drop garbage entries: key must occur in text, value must be short katakana."""
    if not isinstance(words, dict):
        return {}
    out = {}
    for k, v in words.items():
        if not isinstance(k, str) or not isinstance(v, str) or k not in text:
            continue
        if len(k) < 2:
            continue  # particles and single kana carry no useful reading
        reading = _to_katakana(v)
        if _KATAKANA.fullmatch(reading) and len(reading) <= len(k) * 3 + 2:
            out[k] = reading
    return out


_CURRENT_MODEL: str | None = None


def set_current_model(model_id: str) -> None:
    global _CURRENT_MODEL
    _CURRENT_MODEL = model_id


def current_model_id(config_path: str = "config.yaml") -> str:
    if _CURRENT_MODEL:
        return _CURRENT_MODEL
    import yaml

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["llm"]["model"]


class LlmReader:
    def __init__(self, config_path: str = "config.yaml", model_override: str | None = None) -> None:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)["llm"]
        self.model_id: str = model_override or _CURRENT_MODEL or cfg["model"]
        self.device: str = cfg.get("device", "cuda:0")
        cache_path = Path(cfg.get("cache", ".cache/llm_reader.json"))
        if self.model_id != cfg["model"]:
            slug = self.model_id.split("/")[-1].replace(".", "-")
            cache_path = cache_path.with_name(f"{cache_path.stem}_{slug}{cache_path.suffix}")
        self.cache = JsonCache(cache_path)
        self._tok = None
        self._model = None

    def load(self) -> None:
        if self._model is not None:
            return
        self._tok = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            dtype=torch.bfloat16,
            device_map=self.device,
            trust_remote_code=True,
        ).eval()

    def close(self) -> None:
        self._model = None
        self._tok = None
        torch.cuda.empty_cache()

    def read(self, text: str, context: str = "") -> dict[str, object]:
        cached = self.cache.get(context + "\n" + text)
        if cached is not None:
            return dict(cached)
        self.load()
        assert self._model is not None and self._tok is not None
        prompt = f"前文: {context}\n対象: {text}" if context else f"対象: {text}"
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ]
        batch = self._tok.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(self.device)
        input_ids = batch["input_ids"]
        with torch.no_grad():
            out = self._model.generate(
                input_ids,
                max_new_tokens=256,
                do_sample=False,
            )
        decoded = self._tok.decode(out[0][input_ids.shape[1]:], skip_special_tokens=True)
        m = _JSON.search(decoded)
        if m is None:
            result: dict[str, object] = {"words": {}, "ok": False}
        else:
            try:
                parsed = json.loads(m.group(0))
                words = sanitize_words(text, parsed.get("words", {}))
                result = {"words": words, "ok": True}
            except json.JSONDecodeError:
                result = {"words": {}, "ok": False}
        self.cache.set(context + "\n" + text, result)
        return result
