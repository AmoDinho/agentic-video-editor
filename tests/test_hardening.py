from __future__ import annotations

from pathlib import Path

from ave.analysis.pipeline import analyze_folder
from ave.config import AppConfig
from ave.edl.schema import EDL, Segment
from ave.ffmpeg import run
from ave.render.engine import render_edl


def test_missing_audio_render(tmp_path: Path):
    src = tmp_path / "silent.mp4"
    run(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=30:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(src),
        ],
        timeout=30,
    )
    edl = EDL(
        project_id="silent",
        target_duration_s=1.0,
        segments=[
            Segment(
                id="seg_001",
                source=str(src),
                in_s=0.2,
                out_s=1.2,
                role="b_roll",
                reason="silent source",
            )
        ],
    )
    out = tmp_path / "out.mp4"
    render_edl(edl, out, mode="final")
    assert out.is_file()
    from ave.ffmpeg import probe

    streams = {s["codec_type"] for s in probe(out)["streams"]}
    assert "audio" in streams and "video" in streams


def test_corrupt_file_skipped(tmp_path: Path):
    cfg = AppConfig()
    cfg.paths.cache_dir = str(tmp_path / "cache")
    cfg.paths.projects_dir = str(tmp_path / "projects")
    bad = tmp_path / "clips"
    bad.mkdir()
    (bad / "corrupt.mp4").write_bytes(b"not a video")
    results = analyze_folder(bad, config=cfg)
    assert results
    assert results[0].get("status") == "error"
