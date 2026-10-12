from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

from ave.config import AppConfig, load_config
from ave.ffmpeg import run


def caption_shot(
    path: Path,
    in_s: float,
    out_s: float,
    *,
    config: AppConfig | None = None,
) -> list[dict[str, Any]]:
    cfg = config or load_config()
    times = _keyframe_times(in_s, out_s)
    captions: list[dict[str, Any]] = []
    for t in times:
        text = _ollama_caption(path, t, cfg) or f"Shot at {t:.1f}s ({out_s - in_s:.1f}s duration)"
        captions.append({"t": t, "text": text})
    return captions


def _keyframe_times(in_s: float, out_s: float) -> list[float]:
    dur = out_s - in_s
    if dur <= 2:
        return [in_s + dur / 2]
    return [in_s + 0.15, in_s + dur / 2, max(in_s, out_s - 0.15)]


def _ollama_caption(path: Path, t: float, cfg: AppConfig) -> str | None:
    try:
        import httpx
    except Exception:
        return None
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        jpg = Path(tmp.name)
    try:
        run(
            ["-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-q:v", "3", str(jpg)],
            timeout=60,
        )
        b64 = base64.b64encode(jpg.read_bytes()).decode("ascii")
        r = httpx.post(
            f"{cfg.llm.base_url.rstrip('/')}/api/generate",
            json={
                "model": cfg.llm.vision_model,
                "prompt": (
                    "Describe this video frame in one sentence. "
                    "Focus on shot type, subject, and setting."
                ),
                "images": [b64],
                "stream": False,
                "keep_alive": 0,
            },
            timeout=120,
        )
        if r.status_code != 200:
            return None
        return (r.json().get("response") or "").strip() or None
    except Exception:
        return None
    finally:
        jpg.unlink(missing_ok=True)
