"""Phase 4a smoke test: FastAPI endpoints via TestClient."""

from fastapi.testclient import TestClient

from server.app import app

TEXT = "――朝、勇者は「おはよう！」と言った♪\nHPが０になった。"


def main() -> None:
    client = TestClient(app)
    print(client.get("/health").json())
    preview = client.post("/normalize/preview", json={"text": TEXT}).json()
    for chunk in preview["chunks"]:
        print(chunk)
    wav = client.post("/tts", json={"text": "おはよう。"}).content
    print(f"wav bytes={len(wav)}")
    assert wav[:4] == b"RIFF"


if __name__ == "__main__":
    main()
