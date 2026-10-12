"""Worker process. Heavy work never runs in the API.

The loop claims queued analysis jobs and runs one clip at a time through the
existing pipeline. A restart is just another process: finished units stay
finished. Other job kinds are left queued until their phase lands.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from ave.progress.runner import run_job
from ave.progress.store import JobStore


def job_db() -> Path:
    configured = os.environ.get("AVE_JOB_DB")
    if configured:
        return Path(configured)
    from ave.config import load_config

    return load_config().paths.cache / "jobs.sqlite"


def claim_once(store: JobStore) -> str | None:
    row = store.conn.execute(
        "SELECT id, kind FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
    ).fetchone()
    if row is None or row["kind"] != "analyze":
        return None
    from ave.analysis.pipeline import analyze_file
    from ave.ingest.analyze_job import run_analysis_unit

    job_id = row["id"]

    def work(unit: dict) -> None:
        run_analysis_unit(unit, analyze=lambda path: analyze_file(path), store=store, job_id=job_id)

    run_job(store, job_id, work)
    return job_id


def main() -> None:
    print("ave worker up", flush=True)
    while True:
        store = JobStore.open(job_db())
        claimed = claim_once(store)
        if not claimed:
            time.sleep(1)


if __name__ == "__main__":
    main()
