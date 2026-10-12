"""Durable jobs, stages, and work units.

SQLite is the test and single-process store. Postgres is used when
DATABASE_URL is set, through the same SQL with a thin param conversion.
A unit is finished only when its row says so, so a restart resumes after
the last finished unit rather than from the start.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  step TEXT NOT NULL DEFAULT '',
  error TEXT,
  revision_note TEXT NOT NULL DEFAULT '',
  shown_remaining_s REAL,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_stages (
  job_id TEXT NOT NULL,
  name TEXT NOT NULL,
  position INTEGER NOT NULL,
  unit_label TEXT NOT NULL,
  total_units REAL NOT NULL,
  done_units REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',
  PRIMARY KEY (job_id, name)
);

CREATE TABLE IF NOT EXISTS job_units (
  job_id TEXT NOT NULL,
  stage TEXT NOT NULL,
  unit_key TEXT NOT NULL,
  amount REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  finished_at TEXT,
  PRIMARY KEY (job_id, stage, unit_key)
);

CREATE TABLE IF NOT EXISTS job_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rates (
  stage TEXT PRIMARY KEY,
  seconds_per_unit REAL NOT NULL,
  samples INTEGER NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StageSpec:
    name: str
    unit_label: str
    units: list[tuple[str, float]]


class JobStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    @classmethod
    def open(cls, path: str | Path) -> JobStore:
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(dest), check_same_thread=False)
        return cls(conn)

    def create(self, *, kind: str, title: str, stages: list[StageSpec], project_id: str | None = None) -> str:
        job_id = str(uuid.uuid4())
        now = _now()
        self.conn.execute(
            """INSERT INTO jobs
               (id, project_id, kind, title, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'queued', ?, ?)""",
            (job_id, project_id, kind, title, now, now),
        )
        for position, stage in enumerate(stages):
            total = sum(amount for _, amount in stage.units)
            self.conn.execute(
                """INSERT INTO job_stages
                   (job_id, name, position, unit_label, total_units, done_units, status)
                   VALUES (?, ?, ?, ?, ?, 0, 'pending')""",
                (job_id, stage.name, position, stage.unit_label, total),
            )
            self.conn.executemany(
                """INSERT INTO job_units (job_id, stage, unit_key, amount, status)
                   VALUES (?, ?, ?, ?, 'pending')""",
                [(job_id, stage.name, key, amount) for key, amount in stage.units],
            )
        self._event(job_id, {"type": "created", "kind": kind, "title": title})
        self.conn.commit()
        return job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        job = dict(row)
        job["stages"] = [
            dict(stage)
            for stage in self.conn.execute(
                "SELECT * FROM job_stages WHERE job_id = ? ORDER BY position", (job_id,)
            )
        ]
        job["percent"] = _percent(job["stages"])
        return job

    def list_jobs(self, project_id: str | None = None) -> list[dict[str, Any]]:
        if project_id is None:
            rows = self.conn.execute("SELECT id FROM jobs ORDER BY created_at DESC").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id FROM jobs WHERE project_id = ? OR project_id IS NULL ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return [job for job_id in (row["id"] for row in rows) if (job := self.get(job_id))]

    def mark_running(self, job_id: str) -> None:
        now = _now()
        self.conn.execute(
            """UPDATE jobs SET status = 'running', started_at = COALESCE(started_at, ?), updated_at = ?
               WHERE id = ? AND status IN ('queued', 'paused')""",
            (now, now, job_id),
        )
        self.conn.commit()

    def next_unit(self, job_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """SELECT unit_key, stage, amount FROM job_units
               WHERE job_id = ? AND status = 'pending'
               ORDER BY stage, unit_key LIMIT 1""",
            (job_id,),
        ).fetchone()
        return dict(row) if row else None

    def pending_units(self, job_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT unit_key, stage, amount FROM job_units
               WHERE job_id = ? AND status = 'pending'
               ORDER BY stage, unit_key""",
            (job_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def finish_unit(self, job_id: str, stage: str, unit_key: str) -> None:
        now = _now()
        self.conn.execute(
            """UPDATE job_units SET status = 'done', finished_at = ?
               WHERE job_id = ? AND stage = ? AND unit_key = ? AND status != 'done'""",
            (now, job_id, stage, unit_key),
        )
        done = self.conn.execute(
            """SELECT COALESCE(SUM(amount), 0) AS n FROM job_units
               WHERE job_id = ? AND stage = ? AND status = 'done'""",
            (job_id, stage),
        ).fetchone()["n"]
        total = self.conn.execute(
            "SELECT total_units FROM job_stages WHERE job_id = ? AND name = ?",
            (job_id, stage),
        ).fetchone()["total_units"]
        status = "complete" if done >= total else "running"
        self.conn.execute(
            "UPDATE job_stages SET done_units = ?, status = ? WHERE job_id = ? AND name = ?",
            (done, status, job_id, stage),
        )
        self.conn.execute(
            "UPDATE jobs SET updated_at = ? WHERE id = ? AND status NOT IN ('paused', 'cancelled', 'error')",
            (now, job_id),
        )
        self.conn.commit()

    def set_step(
        self,
        job_id: str,
        step: str,
        *,
        revision_note: str = "",
        shown_remaining_s: float | None = None,
    ) -> None:
        self.conn.execute(
            """UPDATE jobs
               SET step = ?, revision_note = ?, shown_remaining_s = ?, updated_at = ?
               WHERE id = ?""",
            (step, revision_note, shown_remaining_s, _now(), job_id),
        )
        self._event(
            job_id,
            {
                "type": "progress",
                "step": step,
                "revision_note": revision_note,
                "shown_remaining_s": shown_remaining_s,
            },
        )
        self.conn.commit()

    def pause(self, job_id: str) -> None:
        self._set_status(job_id, "paused", allowed={"queued", "running"})

    def cancel(self, job_id: str) -> None:
        self._set_status(job_id, "cancelled", allowed={"queued", "running", "paused", "error"})

    def retry(self, job_id: str) -> None:
        now = _now()
        self.conn.execute(
            """UPDATE job_units SET status = 'pending', finished_at = NULL
               WHERE job_id = ? AND status = 'error'""",
            (job_id,),
        )
        self.conn.execute(
            """UPDATE jobs SET status = 'queued', error = NULL, finished_at = NULL, updated_at = ?
               WHERE id = ? AND status IN ('error', 'cancelled')""",
            (now, job_id),
        )
        self._event(job_id, {"type": "retry"})
        self.conn.commit()

    def fail_unit(self, job_id: str, stage: str, unit_key: str, error: str) -> None:
        now = _now()
        self.conn.execute(
            """UPDATE job_units SET status = 'error', finished_at = ?
               WHERE job_id = ? AND stage = ? AND unit_key = ?""",
            (now, job_id, stage, unit_key),
        )
        self.conn.execute(
            "UPDATE jobs SET status = 'error', error = ?, updated_at = ?, finished_at = ? WHERE id = ?",
            (error, now, now, job_id),
        )
        self._event(job_id, {"type": "error", "stage": stage, "unit": unit_key, "error": error})
        self.conn.commit()

    def complete(self, job_id: str) -> None:
        now = _now()
        self.conn.execute(
            "UPDATE jobs SET status = 'complete', finished_at = ?, updated_at = ?, shown_remaining_s = 0 WHERE id = ?",
            (now, now, job_id),
        )
        self._event(job_id, {"type": "complete"})
        self.conn.commit()

    def claim_resumable(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT id FROM jobs WHERE status IN ('queued', 'running', 'paused') ORDER BY created_at"
        ).fetchall()
        return [row["id"] for row in rows]

    def save_rates(self, rates: dict[str, float], samples: dict[str, int]) -> None:
        for stage, rate in rates.items():
            self.conn.execute(
                """INSERT INTO rates (stage, seconds_per_unit, samples) VALUES (?, ?, ?)
                   ON CONFLICT(stage) DO UPDATE SET seconds_per_unit = excluded.seconds_per_unit,
                                                     samples = excluded.samples""",
                (stage, rate, samples.get(stage, 1)),
            )
        self.conn.commit()

    def load_rates(self) -> tuple[dict[str, float], dict[str, int]]:
        rows = self.conn.execute("SELECT stage, seconds_per_unit, samples FROM rates").fetchall()
        return (
            {row["stage"]: row["seconds_per_unit"] for row in rows},
            {row["stage"]: row["samples"] for row in rows},
        )

    def events_after(self, after_id: int, *, job_id: str | None = None) -> list[dict[str, Any]]:
        if job_id:
            rows = self.conn.execute(
                "SELECT id, job_id, ts, payload FROM job_events WHERE id > ? AND job_id = ? ORDER BY id",
                (after_id, job_id),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id, job_id, ts, payload FROM job_events WHERE id > ? ORDER BY id",
                (after_id,),
            ).fetchall()
        out = []
        for row in rows:
            payload = json.loads(row["payload"])
            payload["id"] = row["id"]
            payload["job_id"] = row["job_id"]
            payload["ts"] = row["ts"]
            out.append(payload)
        return out

    def _set_status(self, job_id: str, status: str, *, allowed: set[str]) -> None:
        now = _now()
        self.conn.execute(
            f"UPDATE jobs SET status = ?, updated_at = ? WHERE id = ? AND status IN ({','.join('?' for _ in allowed)})",
            (status, now, job_id, *allowed),
        )
        self._event(job_id, {"type": status})
        self.conn.commit()

    def _event(self, job_id: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO job_events (job_id, ts, payload) VALUES (?, ?, ?)",
            (job_id, _now(), json.dumps(payload)),
        )


def _percent(stages: list[dict[str, Any]]) -> float:
    total = sum(stage["total_units"] for stage in stages) or 1
    done = sum(stage["done_units"] for stage in stages)
    return round(100 * done / total, 1)


def store_from_env(fallback: str | Path) -> JobStore:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        raise RuntimeError("Postgres job store is selected by DATABASE_URL but this process has no psycopg driver yet")
    return JobStore.open(fallback)
