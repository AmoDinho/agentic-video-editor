from ave.edl.schema import EDL, OutputSpec, Segment
from ave.export.job import create_export_job, export_cut, frame_count
from ave.progress.store import JobStore


def _edl() -> EDL:
    return EDL(
        project_id="wild-coast",
        output=OutputSpec(fps=30),
        target_duration_s=10,
        segments=[
            Segment(id="a", source="/clips/a.mp4", in_s=0, out_s=4, role="a_roll", reason="Kept the sentence"),
            Segment(id="b", source="/clips/b.mp4", in_s=1, out_s=5, role="b_roll", reason="Scenic wide shot"),
        ],
    )


def test_export_job_counts_frames(tmp_path):
    edl = _edl()
    assert frame_count(edl) == 240
    store = JobStore.open(tmp_path / "jobs.sqlite")
    job_id = create_export_job(store, edl, project_id="wild-coast")
    job = store.get(job_id)
    assert job["stages"][0]["total_units"] == 240


def test_export_writes_video_path_and_timeline(tmp_path):
    edl = _edl()

    def render(sized, video, on_progress):
        video.write_bytes(b"mp4")
        on_progress({"stage": "segment", "index": 0, "total": 2})
        on_progress({"stage": "segment", "index": 1, "total": 2})

    result = export_cut(edl, tmp_path, preset="1080p", timelines=["fcpxml", "otio"], render=render)
    assert Path_exists(result["video"])
    assert result["progress"][-1]["frame"] == result["frames"]
    assert "fcpxml" in result["timelines"]
    assert (tmp_path / "wild-coast.fcpxml").is_file()


def Path_exists(path: str) -> bool:
    from pathlib import Path

    return Path(path).is_file()
