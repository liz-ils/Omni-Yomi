"""Phase 1 smoke test: auto voice single-shot generation."""

import time

from server.tts import SAMPLE_RATE, load_model, speak


def main() -> None:
    model = load_model()
    text = "こんにちは、これはテストです。"
    start = time.perf_counter()
    out = speak(model, text, "smoke_out.wav", num_step=16)
    elapsed = time.perf_counter() - start
    import soundfile as sf

    data, _ = sf.read(str(out))
    print(f"out={out} sec={len(data) / SAMPLE_RATE:.2f} elapsed={elapsed:.2f}s")


if __name__ == "__main__":
    main()
