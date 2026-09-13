"""OmniVoice thin wrapper (Phase 1: auto voice single-shot)."""

from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from omnivoice import OmniVoice, VoiceClonePrompt

MODEL_ID = "k2-fsa/OmniVoice"
SAMPLE_RATE = 24000
VOICES_DIR = Path("voices")


def load_model(device: str = "cuda:0") -> OmniVoice:
    return OmniVoice.from_pretrained(
        MODEL_ID,
        device_map=device,
        dtype=torch.float16,
    )


def generate(model: OmniVoice, text: str, **kwargs) -> np.ndarray:
    return model.generate(text=text, **kwargs)[0]


def speak(model: OmniVoice, text: str, out_path: str | Path, **kwargs) -> Path:
    out_path = Path(out_path)
    sf.write(str(out_path), generate(model, text, **kwargs), SAMPLE_RATE)
    return out_path


def create_voice_prompt(
    model: OmniVoice, ref_audio: str | Path, ref_text: str
) -> VoiceClonePrompt:
    return model.create_voice_clone_prompt(
        ref_audio=str(ref_audio), ref_text=ref_text
    )


def save_prompt(prompt: VoiceClonePrompt, name: str = "narrator") -> Path:
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    path = VOICES_DIR / f"{name}.pt"
    prompt.save(str(path))
    return path


def load_prompt(name: str = "narrator") -> VoiceClonePrompt | None:
    path = VOICES_DIR / f"{name}.pt"
    if not path.exists():
        return None
    return VoiceClonePrompt.load(str(path))
