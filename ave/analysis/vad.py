from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def detect_voice(path: Path, *, threshold: float = 0.5) -> dict[str, Any]:
    speech = _silero(path, threshold=threshold)
    if speech is None:
        speech = _silencedetect(path)
    duration = _duration(path)
    speech = _merge(speech, gap=0.15)
    silence = _invert(speech, duration)
    return {"speech": speech, "silence": silence}


def _silero(path: Path, threshold: float) -> list[dict[str, float]] | None:
    try:
        import torch
    except Exception:
        return None
    try:
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
            verbose=False,
        )
        (get_speech_timestamps, _, read_audio, *_) = utils
        wav = read_audio(str(path), sampling_rate=16000)
        ts = get_speech_timestamps(wav, model, sampling_rate=16000, threshold=threshold)
        return [{"start": t["start"] / 16000, "end": t["end"] / 16000} for t in ts]
    except Exception:
        return None


def _silencedetect(path: Path, noise_db: float = -30.0, min_d: float = 0.3) -> list[dict[str, float]]:
    from ave.ffmpeg import run

    duration = _duration(path)
    result = run(
        [
            "-i",
            str(path),
            "-af",
            f"silencedetect=noise={noise_db}dB:d={min_d}",
            "-f",
            "null",
            "-",
        ],
        check=False,
        timeout=1800,
    )
    starts: list[float] = []
    ends: list[float] = []
    for line in (result.stderr or "").splitlines():
        if "silence_start:" in line:
            m = re.search(r"silence_start:\s*([0-9.]+)", line)
            if m:
                starts.append(float(m.group(1)))
        if "silence_end:" in line:
            m = re.search(r"silence_end:\s*([0-9.]+)", line)
            if m:
                ends.append(float(m.group(1)))
    silence = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else duration
        silence.append({"start": s, "end": e})
    return _invert(silence, duration)


def _invert(regions: list[dict[str, float]], duration: float) -> list[dict[str, float]]:
    out = []
    cursor = 0.0
    for r in sorted(regions, key=lambda x: x["start"]):
        if r["start"] > cursor + 0.01:
            out.append({"start": cursor, "end": r["start"]})
        cursor = max(cursor, r["end"])
    if cursor < duration - 0.01:
        out.append({"start": cursor, "end": duration})
    return out


def _merge(regions: list[dict[str, float]], gap: float) -> list[dict[str, float]]:
    if not regions:
        return []
    ordered = sorted(regions, key=lambda x: x["start"])
    out = [dict(ordered[0])]
    for r in ordered[1:]:
        if r["start"] <= out[-1]["end"] + gap:
            out[-1]["end"] = max(out[-1]["end"], r["end"])
        else:
            out.append(dict(r))
    return out


def _duration(path: Path) -> float:
    from ave.analysis.probe import probe_file

    return probe_file(path)["duration_s"]
