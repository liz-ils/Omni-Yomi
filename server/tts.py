"""OmniVoice thin wrapper (Phase 1: auto voice single-shot)."""

from pathlib import Path

import soundfile as sf
import torch

from omnivoice import OmniVoice

MODEL_ID = "k2-fsa/OmniVoice"
SAMPLE_RATE = 24000


def load_model(device: str = "cuda:0") -> OmniVoice:
    return OmniVoice.from_pretrained(
        MODEL_ID,
        device_map=device,
        dtype=torch.float16,
    )


def speak(model: OmniVoice, text: str, out_path: str | Path, **kwargs) -> Path:
    out_path = Path(out_path)
    audio = model.generate(text=text, **kwargs)
    sf.write(str(out_path), audio[0], SAMPLE_RATE)
    return out_path
