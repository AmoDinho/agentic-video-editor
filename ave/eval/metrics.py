from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ave.edl.schema import EDL


def evaluate(edl: EDL, analyses: list[dict[str, Any]], style: dict[str, Any]) -> dict[str, Any]:
    lengths = [s.duration_s for s in edl.segments]
    runtime = sum(lengths)
    cuts = max(len(edl.segments) - 1, 0)
    cpm = (cuts / runtime) * 60 if runtime else 0.0
    median = float(np.median(lengths)) if lengths else 0.0
    ref_cpm = float(style.get("cuts_per_minute") or 0)
    ref_med = float((style.get("shot_length") or {}).get("median") or 0)
    pacing = 0.0
    if ref_cpm:
        pacing += abs(cpm - ref_cpm) / ref_cpm
    if ref_med:
        pacing += abs(median - ref_med) / ref_med
    dead = _dead_air(edl, analyses)
    dup = _duplicates(edl)
    coverage = _coverage(edl, analyses)
    runtime_error = abs(runtime - edl.target_duration_s) / edl.target_duration_s if edl.target_duration_s else 0
    rejected = 0
    by_path = {a["path"]: a for a in analyses}
    for seg in edl.segments:
        a = by_path.get(seg.source) or by_path.get(str(Path(seg.source).resolve()))
        if not a:
            continue
        for shot in a.get("shots") or []:
            if shot["in_s"] < seg.out_s and shot["out_s"] > seg.in_s:
                if (shot.get("quality") or {}).get("reject"):
                    rejected += 1
    return {
        "runtime_s": runtime,
        "target_duration_s": edl.target_duration_s,
        "runtime_error": runtime_error,
        "cuts_per_minute": cpm,
        "median_shot_s": median,
        "pacing_distance": pacing,
        "dead_air_s": dead,
        "duplicates": dup,
        "coverage": coverage,
        "rejected_shot_count": rejected,
        "segment_count": len(edl.segments),
        "ok": pacing < 0.15 and runtime_error <= 0.10 and dead <= 1.5 * max(len(edl.segments), 1),
    }


def score_run(
    edl: EDL,
    analyses: list[dict[str, Any]],
    style: dict[str, Any],
    *,
    render_s: float | None = None,
) -> dict[str, Any]:
    stats = evaluate(edl, analyses, style)
    stats["render_s"] = render_s
    stats["time_to_first_cut_s"] = None
    return stats


def _dead_air(edl: EDL, analyses: list[dict[str, Any]]) -> float:
    by_path = {Path(a["path"]).name: a for a in analyses}
    total = 0.0
    for seg in edl.segments:
        a = by_path.get(Path(seg.source).name)
        if not a:
            continue
        for r in a.get("vad", {}).get("silence") or []:
            a0, a1 = max(seg.in_s, r["start"]), min(seg.out_s, r["end"])
            gap = a1 - a0
            if gap > 1.5:
                total += gap
    return total


def _duplicates(edl: EDL) -> int:
    n = 0
    ranges = []
    for seg in edl.segments:
        key = Path(seg.source).name
        for k, a, b in ranges:
            if k == key and min(seg.out_s, b) - max(seg.in_s, a) > 0.01:
                n += 1
        ranges.append((key, seg.in_s, seg.out_s))
    return n


def _coverage(edl: EDL, analyses: list[dict[str, Any]]) -> float:
    used = {Path(s.source).name for s in edl.segments}
    total = {Path(a["path"]).name for a in analyses if a.get("status") != "error"}
    if not total:
        return 0.0
    return len(used) / len(total)
