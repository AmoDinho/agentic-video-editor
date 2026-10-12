from __future__ import annotations

from pathlib import Path
from typing import Any

from ave.ffmpeg import probe

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}


def probe_file(path: Path) -> dict[str, Any]:
    data = probe(path)
    fmt = data.get("format") or {}
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(fmt.get("duration") or (video or {}).get("duration") or 0)
    fps = _fps(video) if video else 0.0
    avg_fps = _avg_fps(video) if video else 0.0
    nb_frames = int(video.get("nb_frames") or 0) if video else 0
    is_vfr = False
    if duration > 0 and nb_frames > 0 and fps > 0:
        expected = duration * fps
        is_vfr = abs(nb_frames - expected) / max(expected, 1) > 0.02
    tags = {**(fmt.get("tags") or {}), **((video or {}).get("tags") or {})}
    return {
        "duration_s": duration,
        "width": int(video.get("width") or 0) if video else 0,
        "height": int(video.get("height") or 0) if video else 0,
        "fps": fps,
        "avg_fps": avg_fps or fps,
        "is_vfr": is_vfr,
        "video_codec": (video or {}).get("codec_name"),
        "audio_codec": (audio or {}).get("codec_name"),
        "audio_channels": int(audio.get("channels") or 0) if audio else 0,
        "audio_rate": int(audio.get("sample_rate") or 0) if audio else 0,
        "has_audio": audio is not None,
        "creation_time": tags.get("creation_time") or tags.get("com.apple.quicktime.creationdate"),
        "nb_frames": nb_frames,
    }


def list_media(folder: Path) -> list[Path]:
    files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    return sorted(files)


def _fps(video: dict[str, Any]) -> float:
    for key in ("r_frame_rate", "avg_frame_rate"):
        val = video.get(key) or "0/1"
        if isinstance(val, str) and "/" in val:
            n, d = val.split("/", 1)
            try:
                if float(d) != 0:
                    return float(n) / float(d)
            except ValueError:
                continue
    return 0.0


def _avg_fps(video: dict[str, Any]) -> float:
    val = video.get("avg_frame_rate") or "0/1"
    if isinstance(val, str) and "/" in val:
        n, d = val.split("/", 1)
        try:
            if float(d) != 0:
                return float(n) / float(d)
        except ValueError:
            return 0.0
    return 0.0
