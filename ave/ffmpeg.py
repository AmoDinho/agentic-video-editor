from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class FFmpegError(RuntimeError):
    pass


def which_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FFmpegError("ffmpeg not found on PATH")
    return path


def which_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if not path:
        raise FFmpegError("ffprobe not found on PATH")
    return path


def run(
    args: list[str],
    *,
    timeout: float | None = None,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd = [which_ffmpeg(), "-hide_banner", "-y", *args]
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise FFmpegError(f"ffmpeg failed ({result.returncode}): {err[-4000:]}")
    return result


def probe(path: str | Path) -> dict[str, Any]:
    cmd = [
        which_ffprobe(),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or "").strip()
        raise FFmpegError(f"ffprobe failed for {path}: {err[-2000:]}")
    return json.loads(result.stdout or "{}")


def has_encoder(name: str) -> bool:
    result = subprocess.run(
        [which_ffmpeg(), "-hide_banner", "-encoders"],
        check=False,
        capture_output=True,
        text=True,
    )
    return name in (result.stdout or "")
