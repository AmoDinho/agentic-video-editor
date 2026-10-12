"""Cut versions. Undo, redo, compare, and restore.

A version is a saved cut plus who made it and why. The current version is the
one the player shows. Undo moves the pointer back. It does not delete history,
so redo can return. Locked segments are copied back into a new cut if an edit
dropped them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ave.edl.schema import EDL, Segment


def save_version(root: Path, edl: EDL, *, summary: str, author: str = "You") -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    history = _load(root)
    number = len(history["versions"]) + 1
    entry = {
        "number": number,
        "summary": summary,
        "author": author,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "edl": json.loads(edl.model_dump_json()),
    }
    history["versions"].append(entry)
    history["cursor"] = number
    _write(root, history)
    return entry


def list_versions(root: Path) -> list[dict[str, Any]]:
    history = _load(root)
    cursor = history["cursor"]
    return [
        {
            "number": item["number"],
            "summary": item["summary"],
            "author": item["author"],
            "created_at": item["created_at"],
            "current": item["number"] == cursor,
        }
        for item in history["versions"]
    ]


def current(root: Path) -> EDL | None:
    history = _load(root)
    item = _at(history, history["cursor"])
    if not item:
        return None
    return EDL.model_validate(item["edl"])


def undo(root: Path) -> EDL | None:
    history = _load(root)
    if history["cursor"] <= 1:
        return current(root)
    history["cursor"] -= 1
    _write(root, history)
    return current(root)


def redo(root: Path) -> EDL | None:
    history = _load(root)
    if history["cursor"] >= len(history["versions"]):
        return current(root)
    history["cursor"] += 1
    _write(root, history)
    return current(root)


def restore(root: Path, number: int) -> EDL:
    history = _load(root)
    item = _at(history, number)
    if not item:
        raise KeyError(number)
    history["cursor"] = number
    _write(root, history)
    return EDL.model_validate(item["edl"])


def keep_locked(previous: EDL | None, updated: EDL) -> EDL:
    if previous is None:
        return updated
    locked = [segment for segment in previous.segments if segment.locked]
    if not locked:
        return updated
    kept = list(updated.segments)
    for segment in locked:
        if not any(_same(segment, other) for other in kept):
            kept.append(segment.model_copy(update={"locked": True}))
    kept.sort(key=lambda segment: (segment.source, segment.in_s))
    return updated.model_copy(update={"segments": kept})


def strike_words(edl: EDL, segment_id: str, words: list[dict[str, Any]], strike: set[int]) -> EDL:
    """Remove struck words by tightening the segment to the words that remain.

    The caller validates the result. Striking every word removes the segment.
    """
    remaining = [word for index, word in enumerate(words) if index not in strike]
    segments = []
    for segment in edl.segments:
        if segment.id != segment_id:
            segments.append(segment)
            continue
        if not remaining:
            continue
        start = float(remaining[0]["start"])
        end = float(remaining[-1]["end"])
        if end - start < 0.3:
            continue
        segments.append(segment.model_copy(update={"in_s": round(start, 3), "out_s": round(end, 3)}))
    return edl.model_copy(update={"segments": segments})


def _same(left: Segment, right: Segment) -> bool:
    return left.source == right.source and abs(left.in_s - right.in_s) < 0.05 and abs(left.out_s - right.out_s) < 0.05


def _load(root: Path) -> dict[str, Any]:
    path = root / "versions.json"
    if not path.is_file():
        return {"versions": [], "cursor": 0}
    return json.loads(path.read_text())


def _write(root: Path, history: dict[str, Any]) -> None:
    (root / "versions.json").write_text(json.dumps(history, indent=2))


def _at(history: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next((item for item in history["versions"] if item["number"] == number), None)
