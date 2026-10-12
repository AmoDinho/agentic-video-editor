from pathlib import Path

from ave.ingest.analyze_job import create_analysis_job, run_analysis_unit
from ave.ingest.cards import clip_card, group_cards, style_sentence
from ave.progress.runner import run_job
from ave.progress.store import JobStore


def test_style_sentence_uses_plain_language():
    text = style_sentence(
        {
            "cuts_per_minute": 9.2,
            "shot_length": {"p10": 2.1, "p90": 5.4},
            "speech_share": 0.6,
            "runtime_s": 8 * 60,
        }
    )
    assert text == "About 9 cuts a minute, most shots 2–5 s, 60% talking, around 8 minutes."


def test_failed_clip_names_the_fix_and_offers_retry():
    card = clip_card(
        {"status": "error", "error": "Unsupported codec: hevc", "probe": {"duration_s": 12}},
        path="/Volumes/T7/GoPro/GOPR0193.MP4",
    )
    assert card["retry"] is True
    assert card["camera"] == "GoPro"
    assert "H.264" in card["error"]
    assert "Talking" not in str(card["kind"])


def test_cards_group_by_day_and_camera_in_shooting_order():
    cards = [
        clip_card(
            {"shot_at": "2026-10-03T12:20:00", "status": "complete", "shots": [{"role_hint": "b_roll"}]},
            path="/x/GOPR0190.MP4",
        ),
        clip_card(
            {"shot_at": "2026-10-03T08:52:00", "status": "complete", "shots": [{"role_hint": "a_roll"}]},
            path="/x/IMG_2031.MOV",
        ),
        clip_card({"shot_at": "2026-10-04T09:00:00", "status": "pending"}, path="/x/IMG_2100.MOV"),
    ]
    groups = group_cards(cards)
    assert groups[0]["camera"] == "iPhone"
    assert groups[0]["clips"][0]["kind"] == "Talking"
    assert groups[1]["camera"] == "GoPro"
    assert groups[2]["day"] == "2026-10-04"


def test_analysis_job_writes_each_clip_and_resumes(tmp_path: Path):
    clips = [tmp_path / f"clip-{i}.mp4" for i in range(4)]
    for clip in clips:
        clip.write_bytes(b"not-a-real-video")
    from ave.progress.store import StageSpec

    store = JobStore.open(tmp_path / "jobs.sqlite")
    job_id = store.create(
        kind="analyze",
        title="Analysing footage · 4 clips",
        stages=[StageSpec("clips", "clips", [(str(clip), 1.0) for clip in clips])],
    )
    written: list[str] = []

    def analyze(path: str) -> dict:
        written.append(path)
        if Path(path).name == "clip-1.mp4":
            store.pause(job_id)
        return {
            "status": "complete",
            "path": path,
            "probe": {"duration_s": 3, "has_audio": True},
            "shots": [{"role_hint": "a_roll"}],
        }

    def work(unit: dict) -> None:
        run_analysis_unit(unit, analyze=analyze, store=store, job_id=job_id)

    assert run_job(store, job_id, work) == "paused"
    assert len(written) == 2
    reopened = JobStore.open(tmp_path / "jobs.sqlite")
    from ave.progress.runner import resume

    assert resume(reopened, job_id, work) == "complete"
    assert [Path(path).name for path in written] == ["clip-0.mp4", "clip-1.mp4", "clip-2.mp4", "clip-3.mp4"]


def test_create_analysis_job_uses_real_files(tmp_path: Path, monkeypatch):
    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "b.MOV").write_bytes(b"y")
    monkeypatch.setattr("ave.ingest.analyze_job._duration_hint", lambda _path: 2.0)
    store = JobStore.open(tmp_path / "jobs.sqlite")
    job_id = create_analysis_job(store, tmp_path)
    job = store.get(job_id)
    assert job is not None
    assert job["stages"][0]["total_units"] == 4.0
    assert len(store.pending_units(job_id)) == 2
