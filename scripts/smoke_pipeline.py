"""Phase 2 smoke test: clean -> split -> normalize."""

from server.pipeline.cleaner import clean
from server.pipeline.normalizer import apply_yomi, detect_lang, normalize_text, readings
from server.pipeline.splitter import split_chunks

SAMPLE = """――１２月３日の朝、勇者は「おはよう！」と言った♪
HPが０になった敵は、This is a penと呟いて消えた。
※ここは注釈です。
"""


def main() -> None:
    cleaned = clean(SAMPLE)
    print("=== cleaned ===")
    print(cleaned)
    print("=== chunks ===")
    for chunk in split_chunks(cleaned):
        norm = normalize_text(apply_yomi(chunk["text"], {}))
        print(f"[{chunk['kind']}/{detect_lang(norm)}] {norm}")
    print("=== readings ===")
    print(readings("勇者はおはようと言った"))


if __name__ == "__main__":
    main()
