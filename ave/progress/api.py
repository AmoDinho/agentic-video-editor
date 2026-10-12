"""Job routes. Mounted beside the existing project routes.

The stream reads the durable event log, so a refresh does not lose progress.
It sleeps long enough that a client never sees more than 4 events a second.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ave.progress.store import JobStore

router = APIRouter()
MIN_INTERVAL_S = 0.25


def job_db_path() -> Path:
    from ave.config import load_config

    return load_config().paths.cache / "jobs.sqlite"


def open_store() -> JobStore:
    return JobStore.open(job_db_path())


def public_job(job: dict[str, Any]) -> dict[str, Any]:
    remaining = job.get("shown_remaining_s")
    return {
        "id": job["id"],
        "project_id": job["project_id"],
        "kind": job["kind"],
        "title": job["title"],
        "status": job["status"],
        "step": job["step"] or "Estimating time…",
        "percent": job["percent"],
        "error": job["error"],
        "revision_note": job["revision_note"],
        "remaining_label": _label(remaining, job["status"]),
        "stages": [
            {
                "name": stage["name"],
                "unit_label": stage["unit_label"],
                "done_units": stage["done_units"],
                "total_units": stage["total_units"],
                "status": stage["status"],
                "percent": round(100 * stage["done_units"] / stage["total_units"], 1) if stage["total_units"] else 0,
            }
            for stage in job["stages"]
        ],
    }


def _label(seconds: float | None, status: str) -> str:
    from ave.progress.estimates import round_remaining

    if status == "complete":
        return "Done"
    if status in {"paused", "cancelled", "error"}:
        return status.capitalize()
    return round_remaining(seconds)


@router.get("/jobs")
def list_jobs(project_id: str | None = None) -> list[dict[str, Any]]:
    store = open_store()
    return [public_job(job) for job in store.list_jobs(project_id)]


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = open_store().get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return public_job(job)


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: str) -> dict[str, Any]:
    return _act(job_id, "pause")


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, Any]:
    return _act(job_id, "cancel")


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str) -> dict[str, Any]:
    return _act(job_id, "retry")


def _act(job_id: str, op: str) -> dict[str, Any]:
    store = open_store()
    if not store.get(job_id):
        raise HTTPException(404, "job not found")
    getattr(store, op)(job_id)
    job = store.get(job_id)
    assert job is not None
    return public_job(job)


@router.get("/events/jobs")
async def stream(after: int = 0):
    async def gen():
        cursor = after
        store = open_store()
        while True:
            batch = store.events_after(cursor)
            if batch:
                cursor = batch[-1]["id"]
                yield {"data": json.dumps({"events": batch})}
            await asyncio.sleep(MIN_INTERVAL_S)

    return EventSourceResponse(gen())
