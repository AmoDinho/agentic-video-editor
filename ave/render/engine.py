from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from ave.config import AppConfig, load_config
from ave.edl.schema import EDL, Segment
from ave.ffmpeg import FFmpegError, has_encoder, run

RenderMode = Literal["preview", "final"]


def render_edl(
    edl: EDL,
    output: str | Path,
    *,
    mode: RenderMode = "final",
    base: Path | None = None,
    analyses: dict[str, dict] | None = None,
    config: AppConfig | None = None,
    on_progress: Callable[[dict], None] | None = None,
) -> Path:
    cfg = config or load_config()
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    resolved = edl.resolved(base)
    if not resolved.segments:
        raise FFmpegError("EDL has no segments to render")

    fade_s = max(cfg.render.audio_fade_ms, 0) / 1000.0
    w, h = resolved.output.width, resolved.output.height
    fps = resolved.output.fps
    ar = resolved.output.audio_rate
    if mode == "preview":
        h = cfg.render.preview_height
        w = int(round(resolved.output.width * h / resolved.output.height))
        if w % 2:
            w += 1
        if h % 2:
            h += 1

    encoder = _pick_encoder(cfg, mode)
    preview = mode == "preview"

    with tempfile.TemporaryDirectory(prefix="ave-render-") as tmp:
        tmp_path = Path(tmp)
        parts: list[Path] = []
        for i, seg in enumerate(resolved.segments):
            if on_progress:
                on_progress({"stage": "segment", "index": i, "total": len(resolved.segments)})
            src = _source_for(seg, mode, analyses)
            part = tmp_path / f"seg_{i:04d}.mp4"
            try:
                _render_segment(
                    src,
                    seg,
                    part,
                    width=w,
                    height=h,
                    fps=fps,
                    audio_rate=ar,
                    fade_s=fade_s,
                    encoder=encoder,
                    preview=preview,
                )
            except FFmpegError:
                if encoder != "libx264" and has_encoder("libx264"):
                    encoder = "libx264"
                    _render_segment(
                        src,
                        seg,
                        part,
                        width=w,
                        height=h,
                        fps=fps,
                        audio_rate=ar,
                        fade_s=fade_s,
                        encoder=encoder,
                        preview=preview,
                    )
                else:
                    raise
            parts.append(part)

        lst = tmp_path / "concat.txt"
        lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
        cut = tmp_path / "cut.mp4"
        run(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lst),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(cut),
            ],
            timeout=600,
        )
        if mode == "final":
            if on_progress:
                on_progress({"stage": "loudnorm"})
            _loudnorm(cut, out, cfg.render.loudnorm_lufs, audio_rate=ar)
        else:
            out.write_bytes(cut.read_bytes())
    return out


def _source_for(seg: Segment, mode: RenderMode, analyses: dict[str, dict] | None) -> Path:
    src = Path(seg.source)
    if mode == "preview" and analyses:
        for key in (str(src), src.name, str(src.resolve())):
            a = analyses.get(key)
            if a and a.get("proxy_path") and Path(a["proxy_path"]).is_file():
                return Path(a["proxy_path"])
    return src


def _pick_encoder(cfg: AppConfig, mode: RenderMode) -> str:
    preferred = cfg.render.preview_encoder if mode == "preview" else cfg.render.final_encoder
    if has_encoder(preferred):
        return preferred
    if has_encoder("libx264"):
        return "libx264"
    raise FFmpegError("no usable h264 encoder")


def _video_args(encoder: str, preview: bool) -> list[str]:
    if encoder == "h264_videotoolbox":
        return ["-c:v", encoder, "-b:v", "5M" if preview else "12M", "-pix_fmt", "yuv420p"]
    preset = "ultrafast" if preview else "medium"
    crf = "28" if preview else "18"
    return ["-c:v", "libx264", "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p"]


def _exact_duration(duration: float, fps: float) -> float:
    frames = max(1, round(duration * fps))
    return frames / fps


def _render_segment(
    src: Path,
    seg: Segment,
    dest: Path,
    *,
    width: int,
    height: int,
    fps: float,
    audio_rate: int,
    fade_s: float,
    encoder: str,
    preview: bool,
) -> None:
    exact = _exact_duration(seg.duration_s, fps)
    fade = min(fade_s, exact / 4) if exact > 0.05 else 0.0
    fade_out_st = max(exact - fade, 0)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},"
        f"format=yuv420p,setpts=PTS-STARTPTS"
    )
    af = f"aformat=sample_rates={audio_rate}:channel_layouts=stereo,aresample={audio_rate},asetpts=PTS-STARTPTS"
    if fade > 0:
        af += f",afade=t=in:st=0:d={fade:.4f},afade=t=out:st={fade_out_st:.4f}:d={fade:.4f}"
    has_audio = _has_audio(src)
    if preview:
        args = ["-ss", f"{seg.in_s:.6f}", "-i", str(src), "-t", f"{exact:.6f}"]
    else:
        args = ["-i", str(src), "-ss", f"{seg.in_s:.6f}", "-t", f"{exact:.6f}"]
    if has_audio:
        args += [
            "-vf",
            vf,
            "-af",
            af,
        ]
    else:
        args += [
            "-f",
            "lavfi",
            "-t",
            f"{exact:.6f}",
            "-i",
            f"anullsrc=channel_layout=stereo:sample_rate={audio_rate}",
            "-filter_complex",
            f"[0:v]{vf}[v];[1:a]aformat=sample_rates={audio_rate}:channel_layouts=stereo,asetpts=PTS-STARTPTS[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
        ]
    args += [
        *_video_args(encoder, preview),
        "-c:a",
        "aac",
        "-ar",
        str(audio_rate),
        "-ac",
        "2",
        "-b:a",
        "192k",
        "-t",
        f"{exact:.6f}",
        str(dest),
    ]
    run(args, timeout=600)


def _has_audio(path: Path) -> bool:
    try:
        from ave.ffmpeg import probe

        data = probe(path)
        return any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    except Exception:
        return False


def _loudnorm(src: Path, dest: Path, lufs: float, *, audio_rate: int) -> None:
    args = [
        "-i",
        str(src),
        "-af",
        f"loudnorm=I={lufs}:TP=-1.5:LRA=11",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        str(audio_rate),
        "-ac",
        "2",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    try:
        run(args, timeout=3600)
    except FFmpegError:
        dest.write_bytes(src.read_bytes())
