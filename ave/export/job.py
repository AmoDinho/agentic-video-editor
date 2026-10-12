"""Background export.

The render reports frames, not a spinner. A finished export also writes the
timeline files the user asked for. Showing the file in a folder is a UI action
on the path this returns.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ave.edl.schema import EDL
from ave.export.otio import export_timeline
from ave.progress.store import JobStore, StageSpec

PRESETS = {
    "1080p": {"width": 1920, "height": 1080, "label": "H.264 · for sharing"},
    "4k": {"width": 3840, "height": 2160, "label": "ProRes 422"},
    "720p": {"width": 1280, "height": 720, "label": "H.264 · small"},
}


def frame_count(edl: EDL) -> int:
    return max(1, round(edl.duration_s * edl.output.fps))


def create_export_job(store: JobStore, edl: EDL, *, project_id: str | None = None) -> str:
    frames = frame_count(edl)
    return store.create(
        kind="export",
        title="Exporting video",
        project_id=project_id,
        stages=[StageSpec("frames", "frames", [(f"{index:06d}", 1.0) for index in range(frames)])],
    )


def export_cut(
    edl: EDL,
    dest_dir: Path,
    *,
    preset: str = "1080p",
    timelines: list[str] | None = None,
    render=None,
) -> dict[str, Any]:
    spec = PRESETS[preset]
    dest_dir.mkdir(parents=True, exist_ok=True)
    video = dest_dir / f"{edl.project_id}.mp4"
    output = edl.output.model_copy(update={"width": spec["width"], "height": spec["height"]})
    sized = edl.model_copy(update={"output": output})
    progress: list[dict[str, Any]] = []

    def on_progress(event: dict[str, Any]) -> None:
        total = len(sized.segments) or 1
        index = event.get("index", 0)
        frames = frame_count(sized)
        event = {**event, "frame": round(frames * (index + 1) / total), "frames": frames}
        progress.append(event)

    if render:
        render(sized, video, on_progress)
    else:
        from ave.render.engine import render_edl

        render_edl(sized, video, mode="final", on_progress=on_progress)
    written = export_timeline(sized, dest_dir)
    wanted = set(timelines or ["fcpxml"])
    return {
        "video": str(video),
        "preset": preset,
        "frames": frame_count(sized),
        "progress": progress,
        "timelines": {key: path for key, path in written.items() if key in wanted or key == "fcpxml"},
    }
