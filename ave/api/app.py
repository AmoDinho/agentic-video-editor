from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ave.config import load_config
from ave.hardware import detect
from ave.jobs import MANAGER
from ave.progress.api import router as jobs_router
from ave.projects import (
    all_projects,
    analyze_project,
    create_project,
    load_analyses_for_project,
    load_edl,
    load_project,
    load_style,
    media_state,
    patch_edl,
    project_dir,
    save_edl,
    set_excluded,
)
from ave.secrets import delete_api_key, has_api_key, set_api_key

app = FastAPI(title="Local Agentic Video Editor")
app.include_router(jobs_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NewProject(BaseModel):
    name: str
    clips_dir: str
    reference_path: str
    target_duration_s: float
    brief: str = ""


class EditRequest(BaseModel):
    note: str = ""
    locked_ids: list[str] = []
    mode: str = "agent"


class EDLPatch(BaseModel):
    op: str
    segment_id: str
    in_s: float | None = None
    out_s: float | None = None


class SettingsIn(BaseModel):
    provider: str | None = None
    model: str | None = None
    vision_model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    api_key_env: str | None = None


class MediaPatch(BaseModel):
    excluded: list[str]


class ExportRequest(BaseModel):
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    dest: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, **detect()}


@app.get("/projects")
def projects() -> list[dict[str, Any]]:
    return all_projects()


@app.post("/projects")
def new_project(body: NewProject) -> dict[str, Any]:
    if not Path(body.clips_dir).expanduser().is_dir():
        raise HTTPException(400, "clips_dir is not a folder")
    if not Path(body.reference_path).expanduser().is_file():
        raise HTTPException(400, "reference_path is not a file")
    return create_project(
        name=body.name,
        clips_dir=body.clips_dir,
        reference_path=body.reference_path,
        target_duration_s=body.target_duration_s,
        brief=body.brief,
    )


@app.get("/projects/{project_id}")
def get_proj(project_id: str) -> dict[str, Any]:
    try:
        return load_project(project_id)
    except KeyError:
        raise HTTPException(404, "project not found")


@app.post("/projects/{project_id}/analyze")
def analyze(project_id: str) -> dict[str, str]:
    load_project(project_id)

    def work(job):
        return analyze_project(project_id, emit=job.emit)

    job = MANAGER.submit(project_id, "analyze", work)
    return {"job_id": job.id}


@app.post("/projects/{project_id}/edit")
def edit(project_id: str, body: EditRequest) -> dict[str, str]:
    rec = load_project(project_id)

    def work(job):
        from ave.agent.loop import run_agent
        from ave.heuristic.assembler import assemble
        from ave.render.engine import render_edl

        cfg = load_config()
        analyses = load_analyses_for_project(project_id, cfg)
        if not analyses:
            analyze_project(project_id, cfg=cfg, emit=job.emit)
            analyses = load_analyses_for_project(project_id, cfg)
        style = load_style(project_id, cfg) or {}
        excluded = set(media_state(project_id, cfg).get("excluded") or [])
        analyses = [a for a in analyses if a.get("path") not in excluded]
        current = load_edl(project_id, cfg)
        locked = []
        if current:
            locked = [s for s in current.segments if s.locked or s.id in body.locked_ids]
        if body.mode == "heuristic":
            edl = assemble(
                analyses,
                style,
                project_id=project_id,
                target_duration_s=rec["target_duration_s"],
                locked=locked,
            )
        else:
            edl = run_agent(
                analyses,
                style,
                project_id=project_id,
                target_duration_s=rec["target_duration_s"],
                brief=rec.get("brief") or "",
                note=body.note,
                locked=locked,
                config=cfg,
                emit=job.emit,
                trace_path=project_dir(project_id, cfg) / "traces" / f"{job.id}.json",
            )
        save_edl(project_id, edl, cfg)
        preview = project_dir(project_id, cfg) / "preview.mp4"
        by_path = {a["path"]: a for a in analyses}
        render_edl(
            edl,
            preview,
            mode="preview",
            analyses=by_path,
            config=cfg,
            on_progress=job.emit,
        )
        return {"edl": json.loads(edl.model_dump_json()), "preview": str(preview)}

    job = MANAGER.submit(project_id, "edit", work)
    return {"job_id": job.id}


@app.get("/projects/{project_id}/edl")
def get_edl(project_id: str) -> dict[str, Any]:
    edl = load_edl(project_id)
    if not edl:
        raise HTTPException(404, "no edl")
    return json.loads(edl.model_dump_json())


@app.patch("/projects/{project_id}/edl")
def patch(project_id: str, body: EDLPatch) -> dict[str, Any]:
    try:
        edl = patch_edl(
            project_id,
            op=body.op,
            segment_id=body.segment_id,
            in_s=body.in_s,
            out_s=body.out_s,
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return json.loads(edl.model_dump_json())


@app.get("/projects/{project_id}/events")
async def events(project_id: str):
    async def gen():
        import asyncio

        cursor = 0
        while True:
            job = MANAGER.latest(project_id)
            if job:
                batch = job.wait_new(cursor, timeout=0.4)
                for ev in batch:
                    cursor += 1
                    yield {"data": json.dumps(ev, default=str)}
                if job.status in {"complete", "error", "cancelled"} and cursor >= len(job.events):
                    yield {"data": json.dumps({"stage": "idle", "status": job.status})}
                    return
            else:
                yield {"data": json.dumps({"stage": "idle"})}
                return
            await asyncio.sleep(0.2)

    return EventSourceResponse(gen())


@app.get("/projects/{project_id}/style")
def style(project_id: str) -> dict[str, Any]:
    data = load_style(project_id)
    if not data:
        raise HTTPException(404, "no style profile")
    return data


@app.get("/projects/{project_id}/media")
def media(project_id: str) -> list[dict[str, Any]]:
    rec = load_project(project_id)
    analyses = load_analyses_for_project(project_id)
    excluded = set(media_state(project_id).get("excluded") or [])
    by_path = {a["path"]: a for a in analyses}
    from ave.analysis.probe import list_media, probe_file
    from ave.analysis.timestamps import shot_timestamp_iso

    rows = []
    for path in list_media(Path(rec["clips_dir"])):
        a = by_path.get(str(path))
        probe = (a or {}).get("probe") or (probe_file(path) if path.is_file() else {})
        rows.append(
            {
                "path": str(path),
                "name": path.name,
                "duration_s": probe.get("duration_s"),
                "shot_at": (a or {}).get("shot_at") or shot_timestamp_iso(path, probe),
                "status": (a or {}).get("status") or "pending",
                "hash": (a or {}).get("file_hash"),
                "quality_flags": [
                    r
                    for s in (a or {}).get("shots") or []
                    for r in (s.get("quality") or {}).get("reject_reasons") or []
                ],
                "included": str(path) not in excluded,
                "proxy": (a or {}).get("proxy_path"),
            }
        )
    rows.sort(key=lambda r: r.get("shot_at") or "")
    return rows


@app.put("/projects/{project_id}/media")
def put_media(project_id: str, body: MediaPatch) -> dict[str, Any]:
    set_excluded(project_id, body.excluded)
    return media_state(project_id)


@app.get("/projects/{project_id}/preview")
def preview(project_id: str):
    path = project_dir(project_id) / "preview.mp4"
    if not path.is_file():
        raise HTTPException(404, "no preview")
    return FileResponse(path, media_type="video/mp4")


@app.post("/projects/{project_id}/export")
def export(project_id: str, body: ExportRequest) -> dict[str, str]:
    load_project(project_id)

    def work(job):
        from ave.export.otio import export_timeline
        from ave.render.engine import render_edl

        cfg = load_config()
        edl = load_edl(project_id, cfg)
        if not edl:
            raise RuntimeError("no edl to export")
        if body.width or body.height or body.fps:
            out = edl.output.model_copy()
            if body.width:
                out.width = body.width
            if body.height:
                out.height = body.height
            if body.fps:
                out.fps = body.fps
            edl = edl.model_copy(update={"output": out})
        dest = Path(body.dest).expanduser() if body.dest else project_dir(project_id, cfg)
        dest.mkdir(parents=True, exist_ok=True)
        mp4 = dest / "export.mp4"
        render_edl(edl, mp4, mode="final", config=cfg, on_progress=job.emit)
        timelines = export_timeline(edl, dest)
        (project_dir(project_id, cfg) / "export.mp4").write_bytes(mp4.read_bytes()) if mp4 != (
            project_dir(project_id, cfg) / "export.mp4"
        ) else None
        return {"mp4": str(mp4), **timelines}

    job = MANAGER.submit(project_id, "export", work)
    return {"job_id": job.id}


@app.get("/media/{asset_id}/proxy")
def proxy(asset_id: str):
    cfg = load_config()
    path = cfg.paths.cache / "assets" / asset_id / "proxy.mp4"
    if not path.is_file():
        for p in (cfg.paths.cache / "assets").glob("*/proxy.mp4"):
            if p.parent.name.startswith(asset_id):
                path = p
                break
    if not path.is_file():
        raise HTTPException(404, "proxy not found")
    return FileResponse(path, media_type="video/mp4")


@app.get("/browse")
def browse(path: str = "") -> dict[str, Any]:
    p = Path(path).expanduser() if path else Path.home()
    if not p.exists():
        raise HTTPException(404, "path not found")
    if p.is_file():
        return {"path": str(p), "type": "file", "name": p.name}
    entries = []
    try:
        children = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        children = []
    for child in children:
        if child.name.startswith("."):
            continue
        entries.append(
            {
                "name": child.name,
                "path": str(child),
                "type": "dir" if child.is_dir() else "file",
                "is_video": child.suffix.lower() in {".mp4", ".mov", ".m4v", ".mkv"},
            }
        )
    return {"path": str(p), "parent": str(p.parent), "entries": entries}


@app.get("/settings")
def get_settings() -> dict[str, Any]:
    cfg = load_config()
    cache = cfg.paths.cache
    size = sum(f.stat().st_size for f in cache.rglob("*") if f.is_file()) if cache.exists() else 0
    return {
        "llm": cfg.llm.model_dump(),
        "has_api_key": has_api_key(cfg.llm.provider, cfg.llm.api_key_env),
        "cache_bytes": size,
        "cache_dir": str(cache),
        "hardware": detect(),
        "cloud_mode": cfg.llm.provider != "ollama",
    }


@app.put("/settings")
def put_settings(body: SettingsIn) -> dict[str, Any]:
    cfg_path = Path("ave.yaml")
    current = json.loads(load_config().model_dump_json())
    llm = current.setdefault("llm", {})
    if body.provider:
        llm["provider"] = body.provider
    if body.model:
        llm["model"] = body.model
    if body.vision_model:
        llm["vision_model"] = body.vision_model
    if body.base_url:
        llm["base_url"] = body.base_url
    if body.api_key_env:
        llm["api_key_env"] = body.api_key_env
    import yaml

    cfg_path.write_text(yaml.safe_dump(current, sort_keys=False))
    if body.api_key:
        set_api_key(body.provider or llm.get("provider") or "ollama", body.api_key)
    return get_settings()


@app.post("/settings/cache/clear")
def clear_cache() -> dict[str, Any]:
    import shutil

    cfg = load_config()
    if cfg.paths.cache.exists():
        shutil.rmtree(cfg.paths.cache)
        cfg.paths.cache.mkdir(parents=True, exist_ok=True)
    return get_settings()


@app.post("/settings/key")
def save_key(body: SettingsIn) -> dict[str, str]:
    if not body.api_key or not body.provider:
        raise HTTPException(400, "provider and api_key required")
    set_api_key(body.provider, body.api_key)
    return {"ok": "true"}


@app.delete("/settings/key/{provider}")
def drop_key(provider: str) -> dict[str, str]:
    delete_api_key(provider)
    return {"ok": "true"}


UI_DIST = Path(__file__).resolve().parents[2] / "ui" / "dist"
if UI_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="ui")
