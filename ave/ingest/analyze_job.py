"""Run analysis as a durable job.

Each clip is one work unit. The unit is marked done only after analyze_file
returns, so a restart continues with the next clip and does not repeat a
finished one. A clip that fails is recorded with a reason and a retry, and
the rest of the folder still runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ave.analysis.probe import list_media
from ave.ingest.cards import clip_card
from ave.progress.store import JobStore, StageSpec


def plan_analysis(folder: str | Path) -> list[Path]:
    return list_media(Path(folder))


def create_analysis_job(store: JobStore, folder: str | Path, *, project_id: str | None = None) -> str:
    files = plan_analysis(folder)
    units = [(str(path), _duration_hint(path)) for path in files]
    if not units:
        units = [("_empty", 0.0)]
    return store.create(
        kind="analyze",
        title=f"Analysing footage · {len(files)} clips",
        project_id=project_id,
        stages=[StageSpec("clips", "clips", units)],
    )


def run_analysis_unit(
    unit: dict[str, Any],
    *,
    analyze: Callable[[str], dict[str, Any]],
    store: JobStore,
    job_id: str,
) -> dict[str, Any]:
    path = unit["unit_key"]
    if path == "_empty":
        return clip_card(None, path=path, name="No clips")
    try:
        analysis = analyze(path)
    except Exception as exc:
        store.fail_unit(job_id, unit["stage"], path, str(exc))
        return clip_card({"status": "error", "error": str(exc), "path": path}, path=path)
    if analysis.get("status") == "error":
        store.fail_unit(job_id, unit["stage"], path, analysis.get("error") or "Analysis failed")
    return clip_card(analysis, path=path)


def _duration_hint(path: Path) -> float:
    try:
        from ave.analysis.probe import probe_file

        return float(probe_file(path).get("duration_s") or 1.0)
    except Exception:
        return 1.0
