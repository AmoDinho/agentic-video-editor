from __future__ import annotations

from pathlib import Path

from ave.edl.schema import EDL, OutputSpec, Segment
from ave.ffmpeg import run


def generate_samples(root: str | Path) -> dict[str, Path]:
    root = Path(root)
    clips = root / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    paths["clip_24"] = _clip(
        clips / "clip_24fps_720p.mp4",
        size="1280x720",
        rate=24,
        duration=8,
        freq=440,
        color="red",
    )
    paths["clip_30"] = _clip(
        clips / "clip_30fps_1080p.mp4",
        size="1920x1080",
        rate=30,
        duration=6,
        freq=660,
        color="green",
    )
    paths["clip_25"] = _clip(
        clips / "clip_25fps_480p.mp4",
        size="854x480",
        rate=25,
        duration=5,
        freq=880,
        color="blue",
    )
    paths["vlog"] = _paced(root / "reference_vlog.mp4", [0.7] * 10, size="1280x720", rate=30)
    paths["doc"] = _paced(root / "reference_doc.mp4", [5.0, 6.0], size="1280x720", rate=24)
    edl = EDL(
        project_id="sample",
        output=OutputSpec(width=1280, height=720, fps=30, audio_rate=48000),
        target_duration_s=6.0,
        segments=[
            Segment(
                id="seg_001",
                source="clips/clip_24fps_720p.mp4",
                in_s=1.0,
                out_s=3.0,
                role="b_roll",
                reason="Opening color card from 24fps clip",
            ),
            Segment(
                id="seg_002",
                source="clips/clip_30fps_1080p.mp4",
                in_s=0.5,
                out_s=2.5,
                role="a_roll",
                reason="Middle stretch from 30fps 1080p clip",
            ),
            Segment(
                id="seg_003",
                source="clips/clip_25fps_480p.mp4",
                in_s=1.0,
                out_s=3.0,
                role="b_roll",
                reason="Close on 25fps 480p clip",
            ),
        ],
        notes="Hand-written Phase 0 EDL mixing three frame rates and resolutions",
    )
    edl_path = root / "sample_edl.json"
    edl.save(edl_path)
    paths["edl"] = edl_path
    return paths


def _clip(dest: Path, *, size: str, rate: int, duration: float, freq: int, color: str) -> Path:
    if dest.is_file():
        return dest
    run(
        [
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={size}:rate={rate}:duration={duration}:alpha=0",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq}:sample_rate=48000:duration={duration}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(dest),
        ],
        timeout=120,
    )
    return dest


def _paced(dest: Path, lengths: list[float], *, size: str, rate: int) -> Path:
    if dest.is_file():
        return dest
    colors = ["red", "green", "blue", "yellow", "cyan", "magenta", "white", "orange", "pink", "purple"]
    parts: list[Path] = []
    tmp = dest.parent / ".tmp_ref"
    tmp.mkdir(parents=True, exist_ok=True)
    for i, dur in enumerate(lengths):
        part = tmp / f"p{i}.mp4"
        color = colors[i % len(colors)]
        run(
            [
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s={size}:d={dur}:r={rate}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={400 + i * 40}:sample_rate=48000:duration={dur}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(part),
            ],
            timeout=60,
        )
        parts.append(part)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    run(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(dest),
        ],
        timeout=120,
    )
    return dest
