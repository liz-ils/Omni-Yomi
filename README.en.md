[![Python](https://img.shields.io/badge/python-3.11-blue?style=for-the-badge&logo=gitlab)](https://www.python.org/)
[![Torch](https://img.shields.io/badge/torch-2.8%2Bcu128-orange?style=for-the-badge&logo=gitlab)](https://pytorch.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge&logo=gitlab)](LICENSE)

# Omni-Yomi

[日本語](README.md)

Japanese novel reader built on OmniVoice.
Extracts web novel text (Narou/Kakuyomu), normalizes it with regex rules and
user dictionaries, resolves difficult kanji readings with a lightweight LLM,
and reads it aloud.

## Features

- Chrome extension for body extraction (ruby kept as `kanji(kana)`)
- Text pipeline: clean -> split (narration/dialogue) -> normalize -> LLM reading
- OmniVoice TTS (auto voice / voice cloning)
- FastAPI server + control page (`http://127.0.0.1:8000/`)
- Swappable LLM via `config.yaml` (default: LFM2.5-1.2B-JP)

## Models

Models are not bundled. They are downloaded from Hugging Face on first run.
Set `llm.model` in `config.yaml` to switch to any compatible model.

## Requirements

- Windows + NVIDIA GPU (CUDA). 8GB works, 12GB+ recommended
- Python 3.11 + uv

## Setup

```bat
uv venv --python 3.11
uv pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
uv pip install omnivoice fugashi unidic-lite
```

## Usage

1. Double-click `start-server.bat` (local helper, not distributed; create it yourself)
2. Open `http://127.0.0.1:8000/`, paste text, preview, play
3. Voice cloning: register a 3-10s reference audio clip with its transcript
4. Extension: load `extension/` in developer mode via `chrome://extensions`

API: `GET /health`, `POST /normalize/preview`, `POST /tts`,
`POST /voices/register`, `GET /voices`

## Credits

| Name | Role | License |
|---|---|---|
| [OmniVoice](https://github.com/k2-fsa/OmniVoice) (k2-fsa) | TTS / voice cloning | Apache-2.0 |
| [PyTorch](https://pytorch.org/) | Inference backend | BSD-3-Clause |
| [Transformers](https://huggingface.co/docs/transformers/) (Hugging Face) | LLM loading | Apache-2.0 |
| [FastAPI](https://fastapi.tiangolo.com/) / [Uvicorn](https://www.uvicorn.org/) | API server | MIT / BSD-3-Clause |
| [fugashi](https://github.com/polm/fugashi) + unidic-lite | Morphological analysis / readings | BSD-3-Clause (dictionaries follow their own terms) |
| [LFM2.5-1.2B-JP](https://huggingface.co/LiquidAI/LFM2.5-1.2B-JP-202606) (Liquid AI, model) | Default reading LLM | LFM License 1.0 (no commercial use above $10M revenue) |
| [MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B) (OpenBMB, model) | Alternative LLM | Apache-2.0 |

## Notes

- Do not use this for unauthorized voice cloning, impersonation, fraud, or scams
  (per OmniVoice terms)
- Respect novel sites' terms of use; do not scrape excessively

## License

MIT ([LICENSE](LICENSE))
