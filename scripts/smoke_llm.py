"""Phase 3 smoke test: LLM yomi for ambiguous readings."""

import json

from server.pipeline.llm_reader import LlmReader
from server.pipeline.normalizer import apply_yomi


def main() -> None:
    reader = LlmReader()
    try:
        for text, context in [
            ("明日、明日香と日本橋で会った。", "登場人物に明日香がいる。舞台は大阪だ。"),
            ("HPが残り1で、彼はAliveと叫んだ。", ""),
        ]:
            result = reader.read(text, context)
            applied = apply_yomi(text, result.get("words", {}))
            print(json.dumps({"in": text, "applied": applied, **result}, ensure_ascii=False))
    finally:
        reader.close()


if __name__ == "__main__":
    main()
