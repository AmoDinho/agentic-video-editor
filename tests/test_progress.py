from __future__ import annotations

from ave.progress.estimates import RateBook, remaining_seconds, round_remaining, smooth_remaining, within_tolerance
from ave.progress.runner import resume, run_job
from ave.progress.store import JobStore, StageSpec


def test_estimate_is_rounded_and_will_not_jump_without_a_reason():
    book = RateBook.empty()
    book.observe("transcription", units=100, elapsed_s=50)
    assert remaining_seconds(book, {"transcription": 100}) == 50
    assert round_remaining(50) == "about 1 min left"
    assert round_remaining(None) == "Estimating time…"

    held, note = smooth_remaining(100, 140)
    assert held == 125
    assert note == ""
    revised, note = smooth_remaining(100, 140, why="Revising: 3 shots need a second look")
    assert revised == 140
    assert "3 shots" in note


def test_simulated_three_minute_job_is_within_twenty_percent_after_fifteen_seconds(tmp_path):
    store = JobStore.open(tmp_path / "jobs.sqlite")
    # 180 one-second units. The clock advances 1s per unit, so the job is 3 minutes.
    stages = [StageSpec("work", "seconds", [(f"{i:03d}", 1.0) for i in range(180)])]
    job_id = store.create(kind="simulate", title="Simulated 3-minute job", stages=stages)
    clock = {"t": 0.0}

    def now() -> float:
        return clock["t"]

    samples: list[tuple[float, float]] = []

    def work(_unit: dict) -> None:
        clock["t"] += 1.0

    def on_tick(tick: dict) -> None:
        elapsed = clock["t"]
        if elapsed >= 15 and tick["shown_remaining_s"] is not None:
            samples.append((tick["shown_remaining_s"], 180 - elapsed))

    status = run_job(store, job_id, work, clock=now, on_tick=on_tick)
    assert status == "complete"
    assert samples
    assert all(within_tolerance(shown, actual) for shown, actual in samples)


def test_restart_resumes_after_the_last_finished_unit(tmp_path):
    store = JobStore.open(tmp_path / "jobs.sqlite")
    stages = [StageSpec("clips", "clips", [(f"clip-{i}", 1.0) for i in range(5)])]
    job_id = store.create(kind="analyze", title="Analysing footage", stages=stages)
    done: list[str] = []

    def work(unit: dict) -> None:
        done.append(unit["unit_key"])
        if unit["unit_key"] == "clip-1":
            store.pause(job_id)

    assert run_job(store, job_id, work) == "paused"
    assert store.pending_units(job_id)[0]["unit_key"] == "clip-2"

    reopened = JobStore.open(tmp_path / "jobs.sqlite")
    assert resume(reopened, job_id, lambda unit: done.append(unit["unit_key"])) == "complete"
    assert done == ["clip-0", "clip-1", "clip-2", "clip-3", "clip-4"]
    assert reopened.get(job_id)["status"] == "complete"


def test_job_routes_pause_and_do_not_invent_a_time(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from ave.api.app import app
    from ave.progress import api as jobs_api

    monkeypatch.setattr(jobs_api, "job_db_path", lambda: tmp_path / "jobs.sqlite")
    store = JobStore.open(tmp_path / "jobs.sqlite")
    job_id = store.create(kind="simulate", title="Simulated job", stages=[StageSpec("work", "seconds", [("a", 1)])])
    client = TestClient(app)
    listed = client.get("/jobs")
    assert listed.status_code == 200
    assert listed.json()[0]["remaining_label"] == "Estimating time…"
    paused = client.post(f"/jobs/{job_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    missing = client.post("/jobs/nope/cancel")
    assert missing.status_code == 404


def test_cancel_and_retry_keep_finished_units(tmp_path):
    store = JobStore.open(tmp_path / "jobs.sqlite")
    job_id = store.create(
        kind="analyze",
        title="Analysing footage",
        stages=[StageSpec("clips", "clips", [("a", 1.0), ("b", 1.0)])],
    )
    store.fail_unit(job_id, "clips", "a", "Unsupported codec: convert to H.264")
    assert store.get(job_id)["status"] == "error"
    store.retry(job_id)
    assert store.get(job_id)["status"] == "queued"
    assert store.next_unit(job_id)["unit_key"] == "a"
