from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FILENAME_PATTERNS = [
    re.compile(r"(20\d{2})[-_](\d{2})[-_](\d{2})[T_\-]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})?"),
    re.compile(r"IMG_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})"),
]


def shot_timestamp(path: Path, probe_meta: dict[str, Any] | None = None) -> datetime:
    if probe_meta:
        raw = probe_meta.get("creation_time")
        parsed = _parse_iso(raw) if raw else None
        if parsed:
            return parsed
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    from_name = _from_filename(path.name)
    return from_name or mtime


def shot_timestamp_iso(path: Path, probe_meta: dict[str, Any] | None = None) -> str:
    return shot_timestamp(path, probe_meta).isoformat()


def _parse_iso(raw: str) -> datetime | None:
    text = raw.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _from_filename(name: str) -> datetime | None:
    for pat in FILENAME_PATTERNS:
        m = pat.search(name)
        if not m:
            continue
        parts = [int(x) if x is not None else 0 for x in m.groups()]
        try:
            year, month, day = parts[0], parts[1], parts[2]
            hour = parts[3] if len(parts) > 3 else 0
            minute = parts[4] if len(parts) > 4 else 0
            second = parts[5] if len(parts) > 5 else 0
            return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
