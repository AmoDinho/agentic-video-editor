from __future__ import annotations

from pathlib import Path

from ave.config import AppConfig
from ave.ffmpeg import FFmpegError, has_encoder, run


def make_proxy(
    src: Path,
    dest: Path,
    *,
    height: int = 540,
    fps: float | None = None,
    config: AppConfig | None = None,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    h = height if height % 2 == 0 else height + 1
    vf = f"scale=-2:{h},setsar=1,format=yuv420p"
    if fps:
        vf += f",fps={fps}"
    encoder = "h264_videotoolbox" if has_encoder("h264_videotoolbox") else "libx264"
    args = ["-i", str(src), "-vf", vf]
    if encoder == "h264_videotoolbox":
        args += ["-c:v", encoder, "-b:v", "2M"]
    else:
        args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "28"]
    args += ["-c:a", "aac", "-ac", "2", "-ar", "48000", "-movflags", "+faststart", str(dest)]
    try:
        run(args, timeout=7200)
    except FFmpegError:
        if encoder != "libx264":
            args = ["-i", str(src), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "28"]
            args += ["-c:a", "aac", "-ac", "2", "-ar", "48000", "-movflags", "+faststart", str(dest)]
            run(args, timeout=7200)
        else:
            raise
    return dest
