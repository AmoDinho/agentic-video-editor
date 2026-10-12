from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any

from ave.ffmpeg import has_encoder, which_ffmpeg, which_ffprobe


def detect() -> dict[str, Any]:
    info: dict[str, Any] = {
        "os": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "ffmpeg": None,
        "ffprobe": None,
        "videotoolbox": False,
        "libx264": False,
        "ollama": False,
        "memory_gb": _memory_gb(),
        "mps": platform.system() == "Darwin" and platform.machine() == "arm64",
        "ok": False,
        "issues": [],
    }
    try:
        info["ffmpeg"] = which_ffmpeg()
        ver = subprocess.run(
            [info["ffmpeg"], "-version"], capture_output=True, text=True, check=False
        )
        info["ffmpeg_version"] = (ver.stdout or "").splitlines()[0] if ver.stdout else ""
    except Exception as exc:
        info["issues"].append(str(exc))
    try:
        info["ffprobe"] = which_ffprobe()
    except Exception as exc:
        info["issues"].append(str(exc))
    if info["ffmpeg"]:
        info["videotoolbox"] = has_encoder("h264_videotoolbox")
        info["libx264"] = has_encoder("libx264")
        if not info["libx264"] and not info["videotoolbox"]:
            info["issues"].append("no h264 encoder found")
    info["ollama"] = _ollama_up()
    info["ok"] = not info["issues"]
    return info


def _memory_gb() -> float | None:
    if platform.system() == "Darwin":
        try:
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                check=True,
            )
            return round(int(out.stdout.strip()) / (1024**3), 1)
        except Exception:
            return None
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * size / (1024**3), 1)
    except Exception:
        return None


def _ollama_up() -> bool:
    if not shutil.which("ollama"):
        return False
    try:
        import httpx

        r = httpx.get("http://localhost:11434/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False
