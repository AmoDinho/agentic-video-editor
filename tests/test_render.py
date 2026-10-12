from __future__ import annotations

from pathlib import Path

from ave.edl.schema import EDL
from ave.ffmpeg import probe
from ave.render.engine import render_edl


def test_render_mixed_rates(samples: dict[str, Path], tmp_path: Path):
    edl = EDL.load(samples["edl"])
    out = tmp_path / "out.mp4"
    render_edl(edl, out, mode="final", base=samples["edl"].parent)
    assert out.is_file()
    meta = probe(out)
    duration = float(meta["format"]["duration"])
    assert 5.5 < duration < 6.6
    streams = {s["codec_type"] for s in meta["streams"]}
    assert "video" in streams and "audio" in streams
    video = next(s for s in meta["streams"] if s["codec_type"] == "video")
    audio = next(s for s in meta["streams"] if s["codec_type"] == "audio")
    assert int(video["width"]) == 1280
    assert int(video["height"]) == 720
    assert int(audio["sample_rate"]) == 48000
