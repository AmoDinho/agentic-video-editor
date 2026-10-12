from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
  path TEXT PRIMARY KEY,
  file_hash TEXT NOT NULL,
  size INTEGER,
  mtime REAL,
  duration_s REAL,
  width INTEGER,
  height INTEGER,
  fps REAL,
  shot_at TEXT,
  analysis_path TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  error TEXT,
  updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_assets_hash ON assets(file_hash);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  clips_dir TEXT NOT NULL,
  reference_path TEXT NOT NULL,
  target_duration_s REAL NOT NULL,
  brief TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  log_path TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_asset(conn: sqlite3.Connection, **fields: Any) -> None:
    fields = {**fields, "updated_at": now()}
    cols = ", ".join(fields)
    placeholders = ", ".join(":" + k for k in fields)
    updates = ", ".join(f"{k}=excluded.{k}" for k in fields if k != "path")
    conn.execute(
        f"INSERT INTO assets ({cols}) VALUES ({placeholders}) ON CONFLICT(path) DO UPDATE SET {updates}",
        fields,
    )
    conn.commit()


def get_asset(conn: sqlite3.Connection, path: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM assets WHERE path = ?", (path,)).fetchone()
    return dict(row) if row else None


def get_asset_by_hash(conn: sqlite3.Connection, file_hash: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM assets WHERE file_hash = ? AND status = 'complete' LIMIT 1",
        (file_hash,),
    ).fetchone()
    return dict(row) if row else None


def upsert_project(conn: sqlite3.Connection, **fields: Any) -> None:
    cols = ", ".join(fields)
    placeholders = ", ".join(":" + k for k in fields)
    updates = ", ".join(f"{k}=excluded.{k}" for k in fields if k != "id")
    conn.execute(
        f"INSERT INTO projects ({cols}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}",
        fields,
    )
    conn.commit()


def list_projects(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_project(conn: sqlite3.Connection, project_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row) if row else None
