"""Phase 5 eval: format adherence + gold recall + latency + VRAM.

Usage: python eval/eval_llm.py [model_id]
Default model comes from config.yaml. Results go to eval/results_<slug>.json.
"""

import json
import sys
import time
from pathlib import Path

import torch

from server.pipeline.llm_reader import LlmReader


def gold_recall(words: dict, gold: dict) -> float:
    if not gold:
        return 1.0 if not words else 0.0
    hit = sum(1 for k, v in gold.items() if words.get(k) == v)
    return hit / len(gold)


def slug(model_id: str) -> str:
    return model_id.split("/")[-1].replace(".", "-")


def main() -> None:
    override = sys.argv[1] if len(sys.argv) > 1 else None
    items = [
        json.loads(line)
        for line in Path("eval/yomi_seed.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    reader = LlmReader(model_override=override)
    print(f"model={reader.model_id}")
    torch.cuda.reset_peak_memory_stats()
    try:
        results = []
        for item in items:
            start = time.perf_counter()
            res = reader.read(item["text"], item.get("context", ""))
            elapsed = time.perf_counter() - start
            words = res.get("words", {})
            results.append(
                {
                    "id": item["id"],
                    "ok": res.get("ok"),
                    "latency": round(elapsed, 2),
                    "gold_recall": gold_recall(words, item["gold"]),
                    "words": words,
                    "gold": item["gold"],
                }
            )
    finally:
        reader.close()
    ok_rate = sum(1 for r in results if r["ok"]) / len(results)
    avg_recall = sum(r["gold_recall"] for r in results) / len(results)
    avg_lat = sum(r["latency"] for r in results) / len(results)
    peak_gb = torch.cuda.max_memory_allocated() / 1024**3
    summary = {
        "model": reader.model_id,
        "n": len(results),
        "ok_rate": round(ok_rate, 3),
        "avg_gold_recall": round(avg_recall, 3),
        "avg_latency_s": round(avg_lat, 2),
        "peak_vram_gb": round(peak_gb, 2),
    }
    out = Path(f"eval/results_{slug(reader.model_id)}.json")
    out.write_text(
        json.dumps({"summary": summary, "items": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
