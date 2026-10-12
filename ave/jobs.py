from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable


class Job:
    def __init__(self, project_id: str, kind: str):
        self.id = str(uuid.uuid4())
        self.project_id = project_id
        self.kind = kind
        self.status = "queued"
        self.events: list[dict[str, Any]] = []
        self.cancel = threading.Event()
        self.error: str | None = None
        self.result: Any = None
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: str | None = None
        self._cv = threading.Condition()

    def emit(self, event: dict[str, Any]) -> None:
        payload = {"ts": datetime.now(timezone.utc).isoformat(), "job_id": self.id, **event}
        with self._cv:
            self.events.append(payload)
            self._cv.notify_all()

    def wait_new(self, after: int, timeout: float = 15.0) -> list[dict[str, Any]]:
        with self._cv:
            if after < len(self.events):
                return list(self.events[after:])
            self._cv.wait(timeout=timeout)
            return list(self.events[after:])


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._by_project: dict[str, list[str]] = defaultdict(list)
        self._lock = threading.Lock()

    def submit(self, project_id: str, kind: str, fn: Callable[[Job], Any]) -> Job:
        job = Job(project_id, kind)
        with self._lock:
            self._jobs[job.id] = job
            self._by_project[project_id].append(job.id)

        def _run() -> None:
            job.status = "running"
            job.emit({"stage": "start", "kind": kind})
            try:
                job.result = fn(job)
                job.status = "cancelled" if job.cancel.is_set() else "complete"
            except Exception as exc:
                job.status = "error"
                job.error = str(exc)
                job.emit({"stage": "error", "error": str(exc)})
            job.finished_at = datetime.now(timezone.utc).isoformat()
            job.emit({"stage": "done", "status": job.status})

        threading.Thread(target=_run, daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def latest(self, project_id: str) -> Job | None:
        ids = self._by_project.get(project_id) or []
        if not ids:
            return None
        return self._jobs.get(ids[-1])

    def cancel_project(self, project_id: str) -> None:
        for jid in self._by_project.get(project_id) or []:
            job = self._jobs.get(jid)
            if job and job.status in {"queued", "running"}:
                job.cancel.set()
                job.emit({"stage": "cancel"})


MANAGER = JobManager()
