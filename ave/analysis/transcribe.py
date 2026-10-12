from __future__ import annotations

from pathlib import Path
from typing import Any


def transcribe(path: Path, *, model: str = "large-v3-turbo") -> dict[str, Any]:
    result = _mlx(path, model) or _openai_whisper(path, model)
    if result is None:
        return {"text": "", "words": [], "engine": "none"}
    return result


def _mlx(path: Path, model: str) -> dict[str, Any] | None:
    try:
        import mlx_whisper
    except Exception:
        return None
    name = model
    if not name.startswith("mlx-community/"):
        name = f"mlx-community/whisper-{model}"
    try:
        out = mlx_whisper.transcribe(
            str(path),
            path=name,
            word_timestamps=True,
        )
        return _normalize(out, "mlx-whisper")
    except Exception:
        return None


def _openai_whisper(path: Path, model: str) -> dict[str, Any] | None:
    try:
        import whisper
    except Exception:
        return None
    name = "turbo" if "turbo" in model else model.replace("large-v3-turbo", "turbo")
    try:
        wmodel = whisper.load_model(name)
        out = wmodel.transcribe(str(path), word_timestamps=True)
        return _normalize(out, "whisper")
    except Exception:
        return None


def _normalize(out: dict[str, Any], engine: str) -> dict[str, Any]:
    words: list[dict[str, Any]] = []
    for seg in out.get("segments") or []:
        for w in seg.get("words") or []:
            token = (w.get("word") or w.get("text") or "").strip()
            if not token:
                continue
            words.append(
                {
                    "word": token,
                    "start": float(w.get("start") or 0),
                    "end": float(w.get("end") or 0),
                }
            )
    return {"text": (out.get("text") or "").strip(), "words": words, "engine": engine}
