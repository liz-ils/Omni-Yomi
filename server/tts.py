"""OmniVoice thin wrapper (Phase 1: auto voice single-shot)."""

from pathlib import Path

import numpy as np
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


def generate(model: OmniVoice, text: str, **kwargs) -> np.ndarray:
    return model.generate(text=text, **kwargs)[0]


def speak(model: OmniVoice, text: str, out_path: str | Path, **kwargs) -> Path:
    out_path = Path(out_path)
    sf.write(str(out_path), generate(model, text, **kwargs), SAMPLE_RATE)
    return out_path
