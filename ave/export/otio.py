from __future__ import annotations

from pathlib import Path

from ave.edl.schema import EDL


def export_timeline(edl: EDL, dest_dir: str | Path, *, base: Path | None = None) -> dict[str, str]:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    fcpxml = dest / f"{edl.project_id}.fcpxml"
    cmx = dest / f"{edl.project_id}.edl"
    otio_path = dest / f"{edl.project_id}.otio"
    fcpxml.write_text(_fcpxml(edl, base))
    cmx.write_text(_cmx_edl(edl, base))
    try:
        _otio(edl, otio_path, base)
    except Exception:
        otio_path.write_text(edl.model_dump_json(indent=2))
    return {"fcpxml": str(fcpxml), "edl": str(cmx), "otio": str(otio_path)}


def _otio(edl: EDL, dest: Path, base: Path | None) -> None:
    import opentimelineio as otio

    fps = edl.output.fps
    timeline = otio.schema.Timeline(name=edl.project_id)
    track = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
    audio = otio.schema.Track(name="A1", kind=otio.schema.TrackKind.Audio)
    for seg in edl.segments:
        src = seg.source_path(base)
        available = otio.opentime.TimeRange(
            otio.opentime.RationalTime(0, fps),
            otio.opentime.RationalTime(max(seg.out_s, 0.001) * fps, fps),
        )
        media = otio.schema.ExternalReference(
            target_url=src.resolve().as_uri(),
            available_range=available,
        )
        source_range = otio.opentime.TimeRange(
            otio.opentime.RationalTime(seg.in_s * fps, fps),
            otio.opentime.RationalTime(seg.duration_s * fps, fps),
        )
        clip = otio.schema.Clip(name=seg.id, media_reference=media, source_range=source_range)
        track.append(clip)
        audio.append(clip.clone())
    timeline.tracks.append(track)
    timeline.tracks.append(audio)
    otio.adapters.write_to_file(timeline, str(dest))


def _fcpxml(edl: EDL, base: Path | None) -> str:
    fps = edl.output.fps
    w, h = edl.output.width, edl.output.height
    assets = []
    clips = []
    t = 0.0
    seen: dict[str, str] = {}
    for i, seg in enumerate(edl.segments):
        src = seg.source_path(base)
        aid = seen.get(str(src))
        if not aid:
            aid = f"r{len(seen)+1}"
            seen[str(src)] = aid
            assets.append(
                f'    <asset id="{aid}" name="{src.name}" src="{src.resolve().as_uri()}" '
                f'hasVideo="1" hasAudio="1"/>'
            )
        dur = seg.duration_s
        clips.append(
            f'        <asset-clip name="{seg.id}" ref="{aid}" '
            f'offset="{_rate(t, fps)}" start="{_rate(seg.in_s, fps)}" duration="{_rate(dur, fps)}"/>'
        )
        t += dur
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE fcpxml>\n'
        '<fcpxml version="1.9">\n'
        "  <resources>\n"
        f'    <format id="r0" name="FFVideoFormat{h}p{int(fps)}" '
        f'frameDuration="{_rate(1/fps, fps)}" width="{w}" height="{h}"/>\n'
        + "\n".join(assets)
        + "\n  </resources>\n"
        "  <library>\n"
        '    <event name="AVE">\n'
        f'      <project name="{edl.project_id}">\n'
        f'        <sequence format="r0" duration="{_rate(t, fps)}">\n'
        "          <spine>\n"
        + "\n".join(clips)
        + "\n          </spine>\n"
        "        </sequence>\n"
        "      </project>\n"
        "    </event>\n"
        "  </library>\n"
        "</fcpxml>\n"
    )


def _cmx_edl(edl: EDL, base: Path | None) -> str:
    lines = [f"TITLE: {edl.project_id}", "FCM: NON-DROP FRAME", ""]
    rec = 0.0
    fps = edl.output.fps
    for i, seg in enumerate(edl.segments, start=1):
        src_in = _tc(seg.in_s, fps)
        src_out = _tc(seg.out_s, fps)
        rec_in = _tc(rec, fps)
        rec += seg.duration_s
        rec_out = _tc(rec, fps)
        reel = Path(seg.source).stem[:8].upper()
        lines.append(f"{i:03d}  {reel:<8} V     C        {src_in} {src_out} {rec_in} {rec_out}")
        lines.append(f"* FROM CLIP NAME: {Path(seg.source).name}")
        lines.append(f"* {seg.reason}")
        lines.append("")
    return "\n".join(lines)


def _rate(seconds: float, fps: float) -> str:
    frames = max(0, int(round(seconds * fps)))
    return f"{frames}/{int(round(fps))}s"


def _tc(seconds: float, fps: float) -> str:
    total = int(round(max(seconds, 0) * fps))
    f = int(round(fps)) or 30
    ff = total % f
    total //= f
    ss = total % 60
    total //= 60
    mm = total % 60
    hh = total // 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"
