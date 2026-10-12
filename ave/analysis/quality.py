from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def score_shot(path: Path, in_s: float, out_s: float, samples: int = 5) -> dict[str, Any]:
    frames = _sample_frames(path, in_s, out_s, samples)
    if not frames:
        return {
            "blur": 0.0,
            "motion": 0.0,
            "exposure": 0.0,
            "reject": True,
            "reject_reasons": ["no_frames"],
        }
    blurs = [_laplacian_var(f) for f in frames]
    exposures = [_exposure(f) for f in frames]
    motion = _motion(frames)
    blur = float(np.median(blurs))
    exposure = float(np.median(exposures))
    reasons: list[str] = []
    if blur < 15:
        reasons.append("blurry")
    if exposure < 0.06:
        reasons.append("black")
    if exposure > 0.92:
        reasons.append("overexposed")
    if motion > 28 and blur < 40:
        reasons.append("shaky")
    return {
        "blur": blur,
        "motion": float(motion),
        "exposure": exposure,
        "reject": bool(reasons),
        "reject_reasons": reasons,
    }


def _sample_frames(path: Path, in_s: float, out_s: float, n: int) -> list[np.ndarray]:
    try:
        import cv2
    except Exception:
        return []
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frames = []
    times = np.linspace(in_s, max(in_s, out_s - 1 / max(fps, 1)), n)
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000)
        ok, frame = cap.read()
        if ok and frame is not None:
            frames.append(frame)
    cap.release()
    return frames


def _laplacian_var(frame: np.ndarray) -> float:
    import cv2

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _exposure(frame: np.ndarray) -> float:
    import cv2

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(gray.mean() / 255.0)


def _motion(frames: list[np.ndarray]) -> float:
    if len(frames) < 2:
        return 0.0
    import cv2

    diffs = []
    prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    for f in frames[1:]:
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        if prev.shape != g.shape:
            g = cv2.resize(g, (prev.shape[1], prev.shape[0]))
        diffs.append(float(np.mean(cv2.absdiff(prev, g))))
        prev = g
    return float(np.mean(diffs)) if diffs else 0.0
