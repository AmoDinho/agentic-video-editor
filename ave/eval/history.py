"""Score history. A later run can see a regression without rereading logs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def record(path: Path, name: str, scores: dict[str, Any]) -> None:
    history = json.loads(path.read_text()) if path.is_file() else []
    history.append({"name": name, "at": datetime.now(timezone.utc).isoformat(), "scores": scores})
    path.write_text(json.dumps(history, indent=2))


def regressed(
    path: Path,
    name: str,
    *,
    keys: tuple[str, ...] = ("pacing_distance", "runtime_error", "dead_air_s"),
) -> list[str]:
    history = json.loads(path.read_text()) if path.is_file() else []
    runs = [item for item in history if item["name"] == name]
    if len(runs) < 2:
        return []
    previous, latest = runs[-2]["scores"], runs[-1]["scores"]
    worse = []
    for key in keys:
        if latest.get(key, 0) > previous.get(key, 0) * 1.1 + 0.01:
            worse.append(key)
    return worse
