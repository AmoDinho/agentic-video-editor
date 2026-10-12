"""Run a job unit by unit, publishing a smoothed time remaining.

The clock is injected so a 3-minute job can be simulated in a test. Pause,
cancel, and a missing process are all just status rows: the next process
calls resume and continues from the first unit that is not done.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ave.progress.estimates import RateBook, remaining_seconds, smooth_remaining
from ave.progress.store import JobStore

UnitFn = Callable[[dict[str, Any]], None]


class JobControl:
    def __init__(self, store: JobStore, job_id: str) -> None:
        self.store = store
        self.job_id = job_id

    @property
    def status(self) -> str:
        job = self.store.get(self.job_id)
        return job["status"] if job else "cancelled"


def run_job(
    store: JobStore,
    job_id: str,
    work: UnitFn,
    *,
    book: RateBook | None = None,
    clock: Callable[[], float] | None = None,
    on_tick: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    import time

    now = clock or time.monotonic
    book = book or RateBook.empty()
    saved_rates, saved_samples = store.load_rates()
    book.rates.update(saved_rates)
    book.samples.update(saved_samples)
    control = JobControl(store, job_id)
    store.mark_running(job_id)
    shown: float | None = None

    while True:
        status = control.status
        if status in {"paused", "cancelled"}:
            return status
        unit = store.next_unit(job_id)
        if unit is None:
            store.complete(job_id)
            store.save_rates(book.rates, book.samples)
            return "complete"
        started = now()
        work(unit)
        elapsed = max(0.0, now() - started)
        book.observe(unit["stage"], unit["amount"], elapsed)
        store.finish_unit(job_id, unit["stage"], unit["unit_key"])
        if control.status in {"paused", "cancelled", "error"}:
            return control.status
        remaining = _remaining_by_stage(store, job_id)
        computed = remaining_seconds(book, remaining)
        shown, note = smooth_remaining(shown, computed)
        step = _step_text(store, job_id, unit)
        store.set_step(job_id, step, revision_note=note, shown_remaining_s=shown)
        if on_tick:
            on_tick({"unit": unit, "shown_remaining_s": shown, "computed_remaining_s": computed, "note": note})


def resume(store: JobStore, job_id: str, work: UnitFn, **kwargs: Any) -> str:
    job = store.get(job_id)
    if not job or job["status"] in {"complete", "cancelled"}:
        return job["status"] if job else "missing"
    if job["status"] == "paused":
        store.mark_running(job_id)
    return run_job(store, job_id, work, **kwargs)


def _remaining_by_stage(store: JobStore, job_id: str) -> dict[str, float]:
    totals: dict[str, float] = {}
    for unit in store.pending_units(job_id):
        totals[unit["stage"]] = totals.get(unit["stage"], 0.0) + unit["amount"]
    return totals


def _step_text(store: JobStore, job_id: str, unit: dict[str, Any]) -> str:
    job = store.get(job_id) or {}
    stage = next((item for item in job.get("stages", []) if item["name"] == unit["stage"]), None)
    if not stage:
        return unit["stage"]
    return f"{stage['name']}: {stage['done_units']:.0f} of {stage['total_units']:.0f} {stage['unit_label']}"
