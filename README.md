[![Python](https://img.shields.io/badge/python-3.11-blue?style=for-the-badge&logo=gitlab)](https://www.python.org/)
[![Torch](https://img.shields.io/badge/torch-2.8%2Bcu128-orange?style=for-the-badge&logo=gitlab)](https://pytorch.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge&logo=gitlab)](LICENSE)

# Omni-Yomi

[English](README.en.md)

OmniVoice を使った日本語小説向け読み上げソフト。
ブラウザ上の小説 (なろう/カクヨム) の本文抽出、正規表現・ユーザー辞書による整形、
軽量LLMによる難読漢字の読み付けに対応する。

## 機能

- Chrome拡張による本文抽出 (ルビは `漢字(かな)` として保持)
- テキストパイプライン: 整形 → 分割 (地の文/セリフ) → 正規化 → LLM読み付け
- OmniVoice による読み上げ (Auto voice / ボイスクローン)
- FastAPIサーバー + 操作ページ (`http://127.0.0.1:8000/`)
- LLMは `config.yaml` で差し替え可能 (既定: LFM2.5-1.2B-JP)

## モデルについて

モデルはリポジトリに同梱しない。初回実行時に Hugging Face から取得される。
`config.yaml` の `llm.model` を変えることで任意の対応モデルに切替可能。

## 必要環境

- Windows + NVIDIA GPU (CUDA)。8GB可、12GB以上推奨
- Python 3.11 + uv

## セットアップ

```bat
uv venv --python 3.11
uv pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
uv pip install omnivoice fugashi unidic-lite
```

## 使い方

1. `start-server.bat` をダブルクリック (配布物には含めない、各自作成)
2. `http://127.0.0.1:8000/` を開いて本文を貼り付け→プレビュー→読み上げ
3. 声のクローン: 操作ページの「声」欄でリファレンス音声 (3-10秒) と書き起こしを登録
4. 拡張機能: `chrome://extensions` でデベロッパーモード→ `extension/` を読込

API: `GET /health`, `POST /normalize/preview`, `POST /tts`,
`POST /voices/register`, `GET /voices`

## 主要ライブラリ・クレジット

| 名称 | 用途 | ライセンス |
|---|---|---|
| [OmniVoice](https://github.com/k2-fsa/OmniVoice) (k2-fsa) | TTS・ボイスクローン | Apache-2.0 |
| [PyTorch](https://pytorch.org/) | 推論基盤 | BSD-3-Clause |
| [Transformers](https://huggingface.co/docs/transformers/) (Hugging Face) | LLM読込 | Apache-2.0 |
| [FastAPI](https://fastapi.tiangolo.com/) / [Uvicorn](https://www.uvicorn.org/) | APIサーバー | MIT / BSD-3-Clause |
| [fugashi](https://github.com/polm/fugashi) + unidic-lite | 形態素解析・読み取得 | BSD-3-Clause (辞書は各配布条件に従う) |
| [LFM2.5-1.2B-JP](https://huggingface.co/LiquidAI/LFM2.5-1.2B-JP-202606) (Liquid AI、モデル) | 既定の読み付けLLM | LFM License 1.0 (年商$10M超は商用不可) |
| [MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B) (OpenBMB、モデル) | 切替用LLM | Apache-2.0 |

## 注意

- 他人の声の無断クローン・なりすまし・詐欺等の悪用を禁止する
  (OmniVoice の利用条件に準拠)
- 小説サイトの利用規約を守り、過度な自動取得は行わないこと

## ライセンス

MIT ([LICENSE](LICENSE))
