from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ave.analysis.pipeline import analyze_file
from ave.config import AppConfig, load_config


def build_style_profile(
    reference: str | Path,
    *,
    config: AppConfig | None = None,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_config()
    path = Path(reference).resolve()
    analysis = analysis or analyze_file(path, config=cfg)
    shots = analysis.get("shots") or []
    lengths = [max(s["out_s"] - s["in_s"], 0.0) for s in shots]
    runtime = float(analysis.get("probe", {}).get("duration_s") or sum(lengths))
    cuts = max(len(shots) - 1, 0)
    cuts_per_min = (cuts / runtime) * 60 if runtime else 0.0
    dist = _distribution(lengths)
    speech_share = _speech_share(analysis)
    cut_on_sentence = _cut_on_sentence_end(analysis)
    a_roll_stretches = _a_roll_stretches(shots)
    structure = _structure(runtime)
    profile = {
        "version": 1,
        "reference": str(path),
        "runtime_s": runtime,
        "shot_count": len(shots),
        "cuts_per_minute": cuts_per_min,
        "shot_length": dist,
        "speech_share": speech_share,
        "cuts_on_sentence_end": cut_on_sentence,
        "a_roll_stretch_s": _distribution(a_roll_stretches) if a_roll_stretches else dist,
        "structure": structure,
        "summary": _summary(
            runtime, cuts_per_min, dist, speech_share, cut_on_sentence, a_roll_stretches
        ),
    }
    return profile


def save_profile(profile: dict[str, Any], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(profile, indent=2))


def _distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"median": 0.0, "p10": 0.0, "p90": 0.0, "mean": 0.0}
    arr = np.array(values, dtype=float)
    return {
        "median": float(np.median(arr)),
        "p10": float(np.percentile(arr, 10)),
        "p90": float(np.percentile(arr, 90)),
        "mean": float(np.mean(arr)),
    }


def _speech_share(analysis: dict[str, Any]) -> float:
    runtime = float(analysis.get("probe", {}).get("duration_s") or 0)
    if runtime <= 0:
        return 0.0
    spoken = sum(max(0.0, r["end"] - r["start"]) for r in analysis.get("vad", {}).get("speech") or [])
    return min(1.0, spoken / runtime)


def _cut_on_sentence_end(analysis: dict[str, Any]) -> float:
    words = analysis.get("transcript", {}).get("words") or []
    shots = analysis.get("shots") or []
    if not shots or len(shots) < 2:
        return 0.0
    sentence_ends = []
    for i, w in enumerate(words):
        token = (w.get("word") or "").strip()
        if token.endswith((".", "!", "?")):
            sentence_ends.append(float(w["end"]))
        elif i + 1 < len(words) and float(words[i + 1]["start"]) - float(w["end"]) > 0.35:
            sentence_ends.append(float(w["end"]))
    if not sentence_ends:
        return 0.0
    hits = 0
    cuts = [s["out_s"] for s in shots[:-1]]
    for c in cuts:
        if any(abs(c - e) < 0.25 for e in sentence_ends):
            hits += 1
    return hits / len(cuts) if cuts else 0.0


def _a_roll_stretches(shots: list[dict[str, Any]]) -> list[float]:
    stretches: list[float] = []
    acc = 0.0
    for s in shots:
        role = s.get("role_hint") or ("a_roll" if s.get("speech_share", 0) >= 0.3 else "b_roll")
        dur = s["out_s"] - s["in_s"]
        if role == "a_roll":
            acc += dur
        else:
            if acc > 0:
                stretches.append(acc)
                acc = 0.0
    if acc > 0:
        stretches.append(acc)
    return stretches


def _structure(runtime: float) -> list[dict[str, Any]]:
    if runtime <= 0:
        return []
    open_s = min(12.0, runtime * 0.12)
    close_s = min(15.0, runtime * 0.12)
    body = max(runtime - open_s - close_s, 0)
    return [
        {"name": "opening", "duration_s": open_s},
        {"name": "body", "duration_s": body},
        {"name": "closing", "duration_s": close_s},
    ]


def _summary(
    runtime: float,
    cpm: float,
    dist: dict[str, float],
    speech: float,
    sentence: float,
    stretches: list[float],
) -> str:
    pace = "fast, vlog-like" if cpm >= 12 else "moderate" if cpm >= 6 else "slow, documentary-like"
    cut_style = "usually on sentence ends" if sentence >= 0.5 else "often mid-flow"
    stretch = float(np.median(stretches)) if stretches else dist.get("median", 0)
    return (
        f"A {pace} cut of {runtime:.1f}s with {cpm:.1f} cuts/min. "
        f"Shot lengths median {dist.get('median', 0):.2f}s (p10 {dist.get('p10', 0):.2f}, "
        f"p90 {dist.get('p90', 0):.2f}). Speech covers {speech:.0%} of runtime; cuts {cut_style}. "
        f"Typical A-roll stretch between B-roll inserts is {stretch:.1f}s. "
        f"Structure is a short opening, a longer body, and a brief close."
    )
