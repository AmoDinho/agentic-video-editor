from __future__ import annotations

from pathlib import Path
from typing import Any


def detect_shots(path: Path, *, min_shot_s: float = 0.3, threshold: float = 27.0) -> list[dict[str, Any]]:
    shots = _pyscenedetect(path, threshold=threshold)
    if not shots:
        shots = _ffmpeg_scenes(path, threshold=0.3)
    if not shots:
        shots = _single_shot(path)
    merged: list[dict[str, Any]] = []
    for i, s in enumerate(shots):
        if s["out_s"] - s["in_s"] < min_shot_s and merged:
            merged[-1]["out_s"] = s["out_s"]
            continue
        merged.append({**s, "id": f"shot_{len(merged)+1:03d}"})
    if not merged:
        merged = _single_shot(path)
    for i, s in enumerate(merged):
        s["id"] = f"shot_{i+1:03d}"
    return merged


def _pyscenedetect(path: Path, threshold: float) -> list[dict[str, Any]]:
    try:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import AdaptiveDetector, ContentDetector
    except Exception:
        return []
    try:
        video = open_video(str(path))
        sm = SceneManager()
        sm.add_detector(ContentDetector(threshold=threshold))
        sm.add_detector(AdaptiveDetector())
        sm.detect_scenes(video)
        scenes = sm.get_scene_list()
        out = []
        for start, end in scenes:
            in_s = start.seconds
            out_s = end.seconds
            if out_s > in_s:
                out.append({"in_s": in_s, "out_s": out_s})
        return out
    except Exception:
        return []


def _ffmpeg_scenes(path: Path, threshold: float) -> list[dict[str, Any]]:
    from ave.analysis.probe import probe_file
    from ave.ffmpeg import run

    meta = probe_file(path)
    duration = meta["duration_s"]
    result = run(
        [
            "-i",
            str(path),
            "-filter:v",
            f"select='gt(scene,{threshold})',showinfo",
            "-f",
            "null",
            "-",
        ],
        check=False,
        timeout=1800,
    )
    times = [0.0]
    for line in (result.stderr or "").splitlines():
        if "pts_time:" in line:
            try:
                part = line.split("pts_time:")[1].split()[0]
                times.append(float(part))
            except (IndexError, ValueError):
                continue
    times.append(duration)
    times = sorted(set(round(t, 4) for t in times if 0 <= t <= duration + 0.05))
    shots = []
    for a, b in zip(times, times[1:]):
        if b - a > 0.05:
            shots.append({"in_s": a, "out_s": min(b, duration)})
    return shots


def _single_shot(path: Path) -> list[dict[str, Any]]:
    from ave.analysis.probe import probe_file

    dur = probe_file(path)["duration_s"]
    return [{"id": "shot_001", "in_s": 0.0, "out_s": dur}]
