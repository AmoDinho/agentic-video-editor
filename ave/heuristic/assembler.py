from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from ave.edl.schema import EDL, OutputSpec, Segment
from ave.edl.validator import index_from_analyses, validate_edl


def assemble(
    analyses: list[dict[str, Any]],
    style: dict[str, Any],
    *,
    project_id: str,
    target_duration_s: float,
    output: OutputSpec | None = None,
    locked: list[Segment] | None = None,
    included: set[str] | None = None,
) -> EDL:
    rng = np.random.default_rng(_seed(project_id))
    dist = style.get("shot_length") or {"median": 2.5, "p10": 0.8, "p90": 6.0}
    shots = _collect(analyses, included)
    shots = [s for s in shots if not (s["quality"].get("reject") if s.get("quality") else False)]
    shots.sort(key=lambda s: (s["shot_at"], s["in_s"], s["path"]))

    locked = locked or []
    segments: list[Segment] = []
    used: list[tuple[str, float, float]] = []
    n = 0

    def take(shot: dict[str, Any], in_s: float, out_s: float, role: str, reason: str) -> None:
        nonlocal n
        in_s, out_s = _trim_dead_air(shot, in_s, out_s)
        in_s, out_s = _snap(shot, in_s, out_s)
        if out_s - in_s < 0.3:
            return
        if any(p == shot["path"] and _overlap(in_s, out_s, a, b) for p, a, b in used):
            return
        n += 1
        segments.append(
            Segment(
                id=f"seg_{n:03d}",
                source=shot["path"],
                in_s=round(in_s, 3),
                out_s=round(out_s, 3),
                role=role,  # type: ignore[arg-type]
                reason=reason,
            )
        )
        used.append((shot["path"], in_s, out_s))

    total = 0.0
    for shot in shots:
        if total >= target_duration_s * 1.02:
            break
        role = shot.get("role_hint") or ("a_roll" if shot.get("speech_share", 0) >= 0.3 else "b_roll")
        in_s, out_s = shot["in_s"], shot["out_s"]
        if role == "a_roll":
            in_s, out_s = _speech_span(shot, in_s, out_s)
            reason = "Kept talking stretch whole; cleanest available A-roll in shooting order"
        else:
            want = float(rng.uniform(dist.get("p10", 0.8), dist.get("p90", 6.0)))
            want = min(want, out_s - in_s)
            if want < 0.3:
                continue
            mid = (in_s + out_s) / 2
            in_s = max(shot["in_s"], mid - want / 2)
            out_s = min(shot["out_s"], in_s + want)
            reason = f"B-roll trimmed to {want:.1f}s from reference shot-length distribution"
        remaining = target_duration_s * 1.05 - total
        if remaining < 0.3:
            break
        if out_s - in_s > remaining:
            out_s = in_s + remaining
        take(shot, in_s, out_s, role, reason)
        if segments:
            total = sum(s.duration_s for s in segments)

    if locked:
        segments = _reinsert_locked(segments, locked, shots)

    while sum(s.duration_s for s in segments) > target_duration_s * 1.08 and len(segments) > 1:
        drop_i = max(
            (i for i, s in enumerate(segments) if s.role == "b_roll" and not s.locked),
            default=None,
        )
        if drop_i is None:
            break
        segments.pop(drop_i)

    for i, s in enumerate(segments):
        s.id = f"seg_{i+1:03d}"

    edl = EDL(
        project_id=project_id,
        output=output or OutputSpec(),
        target_duration_s=target_duration_s,
        segments=segments,
        notes=_notes(style, segments, target_duration_s),
    )
    idx = index_from_analyses(analyses)
    result = validate_edl(edl, idx, check_target=False)
    if not result.ok:
        edl = _repair(edl, result, analyses, target_duration_s)
    return edl


def _collect(analyses: list[dict[str, Any]], included: set[str] | None) -> list[dict[str, Any]]:
    out = []
    for a in analyses:
        if a.get("status") == "error":
            continue
        path = a["path"]
        if included is not None and path not in included and Path(path).name not in included:
            continue
        shot_at = a.get("shot_at") or ""
        try:
            dt = datetime.fromisoformat(shot_at.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.min
        for shot in a.get("shots") or []:
            item = dict(shot)
            item["path"] = path
            item["shot_at"] = dt
            item["words"] = a.get("transcript", {}).get("words") or []
            item["vad"] = a.get("vad") or {}
            out.append(item)
    return out


def _speech_span(shot: dict[str, Any], in_s: float, out_s: float) -> tuple[float, float]:
    regions = shot.get("vad", {}).get("speech") or []
    overlap = [r for r in regions if r["end"] > in_s and r["start"] < out_s]
    if not overlap:
        return in_s, out_s
    return max(in_s, min(r["start"] for r in overlap)), min(out_s, max(r["end"] for r in overlap))


def _trim_dead_air(shot: dict[str, Any], in_s: float, out_s: float, max_gap: float = 1.5) -> tuple[float, float]:
    silence = shot.get("vad", {}).get("silence") or []
    for r in silence:
        if r["start"] <= in_s and r["end"] - in_s > 0.2:
            in_s = min(r["end"], out_s - 0.3)
        if r["end"] >= out_s and out_s - r["start"] > 0.2:
            out_s = max(r["start"], in_s + 0.3)
    return in_s, out_s


def _snap(shot: dict[str, Any], in_s: float, out_s: float) -> tuple[float, float]:
    return (
        snap_to_boundary_values(shot, in_s),
        snap_to_boundary_values(shot, out_s),
    )


def snap_to_boundary_values(shot: dict[str, Any], t: float) -> float:
    candidates = [shot.get("in_s", t), shot.get("out_s", t)]
    for w in shot.get("words") or []:
        token = (w.get("word") or "").strip()
        candidates.append(float(w["start"]))
        candidates.append(float(w["end"]))
        if token.endswith((".", "!", "?")):
            candidates.append(float(w["end"]))
    for key in ("speech", "silence"):
        for r in shot.get("vad", {}).get(key) or []:
            candidates.extend([r["start"], r["end"]])
    if not candidates:
        return t
    return min(candidates, key=lambda c: abs(c - t))


def _overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return min(a1, b1) - max(a0, b0) > 1e-3


def _seed(project_id: str) -> int:
    return int(hashlib.sha256(project_id.encode()).hexdigest()[:8], 16)


def _notes(style: dict[str, Any], segments: list[Segment], target: float) -> str:
    total = sum(s.duration_s for s in segments)
    a = sum(1 for s in segments if s.role == "a_roll")
    b = len(segments) - a
    return (
        f"Heuristic cut {total:.1f}s (target {target:.1f}s) with {a} A-roll and {b} B-roll segments. "
        f"Reference: {style.get('summary', '')}"
    )


def _reinsert_locked(
    segments: list[Segment], locked: list[Segment], shots: list[dict[str, Any]]
) -> list[Segment]:
    kept = [s.model_copy(update={"locked": True}) for s in locked]
    others = [
        s
        for s in segments
        if not any(
            Path(s.source).name == Path(lk.source).name and _overlap(s.in_s, s.out_s, lk.in_s, lk.out_s)
            for lk in locked
        )
    ]
    combined = kept + others

    def key(seg: Segment) -> tuple:
        match = next((sh for sh in shots if Path(sh["path"]).name == Path(seg.source).name), None)
        dt = match["shot_at"] if match else datetime.min
        return (dt, seg.in_s)

    combined.sort(key=key)
    return combined


def _repair(edl: EDL, result, analyses, target) -> EDL:
    segs = list(edl.segments)
    drop_ids = {
        e.segment_id
        for e in result.errors
        if e.code in {"too_short", "mid_word", "out_of_range"} and e.segment_id
    }
    segs = [s for s in segs if s.id not in drop_ids]
    for i, s in enumerate(segs):
        s.id = f"seg_{i+1:03d}"
    return edl.model_copy(update={"segments": segs, "notes": edl.notes + " (repaired)"})
