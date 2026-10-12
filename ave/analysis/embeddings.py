from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from ave.ffmpeg import run

_CLIP = None


def embed_shot(path: Path, times: list[float]) -> list[float] | None:
    vectors = []
    for t in times:
        vec = _embed_frame(path, t)
        if vec is not None:
            vectors.append(vec)
    if not vectors:
        return None
    mean = np.mean(np.stack(vectors), axis=0)
    n = np.linalg.norm(mean)
    if n:
        mean = mean / n
    return mean.astype(float).tolist()


def embed_text(query: str) -> list[float] | None:
    model = _clip()
    if model is None:
        return None
    model_obj, preprocess, tokenizer, device = model
    import torch

    tokens = tokenizer([query])
    with torch.no_grad():
        vec = model_obj.encode_text(tokens.to(device))
        vec = vec / vec.norm(dim=-1, keepdim=True)
    return vec[0].cpu().numpy().astype(float).tolist()


def cosine(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def _embed_frame(path: Path, t: float) -> np.ndarray | None:
    model = _clip()
    if model is None:
        return None
    model_obj, preprocess, tokenizer, device = model
    import torch
    from PIL import Image

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        jpg = Path(tmp.name)
    try:
        run(
            ["-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-q:v", "3", str(jpg)],
            timeout=60,
        )
        img = preprocess(Image.open(jpg).convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            vec = model_obj.encode_image(img)
            vec = vec / vec.norm(dim=-1, keepdim=True)
        return vec[0].cpu().numpy()
    except Exception:
        return None
    finally:
        jpg.unlink(missing_ok=True)


def _clip() -> tuple[Any, Any, Any, Any] | None:
    global _CLIP
    if _CLIP is not None:
        return _CLIP
    try:
        import open_clip
        import torch
    except Exception:
        return None
    try:
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="openai"
        )
        model = model.to(device).eval()
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        _CLIP = (model, preprocess, tokenizer, device)
        return _CLIP
    except Exception:
        return None
