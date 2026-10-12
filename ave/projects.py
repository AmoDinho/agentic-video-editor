from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ave.analysis.pipeline import analyze_file, analyze_folder, load_analysis
from ave.config import AppConfig, load_config
from ave.db import connect, get_project, list_projects, upsert_project
from ave.edl.schema import EDL, Segment
from ave.edl.validator import index_from_analyses, validate_edl
from ave.style.profile import build_style_profile, save_profile


def db(cfg: AppConfig | None = None):
    cfg = cfg or load_config()
    return connect(cfg.paths.cache / "ave.sqlite"), cfg


def create_project(
    *,
    name: str,
    clips_dir: str | Path,
    reference_path: str | Path,
    target_duration_s: float,
    brief: str = "",
    config: AppConfig | None = None,
) -> dict[str, Any]:
    conn, cfg = db(config)
    pid = slug(name) + "-" + uuid.uuid4().hex[:6]
    now = datetime.now(timezone.utc).isoformat()
    clips_dir = str(Path(clips_dir).expanduser().resolve())
    reference_path = str(Path(reference_path).expanduser().resolve())
    rec = {
        "id": pid,
        "name": name,
        "clips_dir": clips_dir,
        "reference_path": reference_path,
        "target_duration_s": float(target_duration_s),
        "brief": brief,
        "created_at": now,
        "updated_at": now,
    }
    upsert_project(conn, **rec)
    root = project_dir(pid, cfg)
    root.mkdir(parents=True, exist_ok=True)
    (root / "project.json").write_text(json.dumps(rec, indent=2))
    (root / "media.json").write_text(json.dumps({"excluded": []}, indent=2))
    return rec


def slug(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    return (cleaned or "project")[:40]


def project_dir(project_id: str, cfg: AppConfig | None = None) -> Path:
    cfg = cfg or load_config()
    return cfg.paths.projects / project_id


def load_project(project_id: str, cfg: AppConfig | None = None) -> dict[str, Any]:
    conn, cfg = db(cfg)
    rec = get_project(conn, project_id)
    if rec:
        return rec
    p = project_dir(project_id, cfg) / "project.json"
    if p.is_file():
        return json.loads(p.read_text())
    raise KeyError(project_id)


def all_projects(cfg: AppConfig | None = None) -> list[dict[str, Any]]:
    conn, cfg = db(cfg)
    rows = list_projects(conn)
    if rows:
        return [_enrich(r, cfg) for r in rows]
    out = []
    for p in cfg.paths.projects.glob("*/project.json"):
        rec = json.loads(p.read_text())
        out.append(_enrich(rec, cfg))
    return out


def _enrich(rec: dict[str, Any], cfg: AppConfig) -> dict[str, Any]:
    root = project_dir(rec["id"], cfg)
    edl_path = root / "edl.json"
    rec = dict(rec)
    rec["clip_count"] = _clip_count(rec.get("clips_dir"))
    rec["has_edl"] = edl_path.is_file()
    rec["has_preview"] = (root / "preview.mp4").is_file()
    rec["has_export"] = (root / "export.mp4").is_file()
    rec["runtime_s"] = None
    if edl_path.is_file():
        try:
            rec["runtime_s"] = EDL.load(edl_path).duration_s
        except Exception:
            pass
    rec["last_export"] = (
        datetime.fromtimestamp((root / "export.mp4").stat().st_mtime, tz=timezone.utc).isoformat()
        if (root / "export.mp4").is_file()
        else None
    )
    return rec


def _clip_count(folder: str | None) -> int:
    if not folder or not Path(folder).is_dir():
        return 0
    from ave.analysis.probe import list_media

    return len(list_media(Path(folder)))


def media_state(project_id: str, cfg: AppConfig | None = None) -> dict[str, Any]:
    root = project_dir(project_id, cfg)
    p = root / "media.json"
    if p.is_file():
        return json.loads(p.read_text())
    return {"excluded": []}


def set_excluded(project_id: str, excluded: list[str], cfg: AppConfig | None = None) -> None:
    root = project_dir(project_id, cfg)
    (root / "media.json").write_text(json.dumps({"excluded": excluded}, indent=2))


def save_edl(project_id: str, edl: EDL, cfg: AppConfig | None = None) -> Path:
    path = project_dir(project_id, cfg) / "edl.json"
    edl.save(path)
    return path


def load_edl(project_id: str, cfg: AppConfig | None = None) -> EDL | None:
    path = project_dir(project_id, cfg) / "edl.json"
    if path.is_file():
        return EDL.load(path)
    return None


def load_analyses_for_project(project_id: str, cfg: AppConfig | None = None) -> list[dict[str, Any]]:
    cfg = cfg or load_config()
    rec = load_project(project_id, cfg)
    from ave.analysis.probe import list_media

    out = []
    for path in list_media(Path(rec["clips_dir"])):
        a = load_analysis(path, cfg)
        if a:
            out.append(a)
    return out


def analyze_project(
    project_id: str,
    *,
    cfg: AppConfig | None = None,
    emit=None,
) -> dict[str, Any]:
    cfg = cfg or load_config()
    rec = load_project(project_id, cfg)
    clips = analyze_folder(rec["clips_dir"], config=cfg, emit=emit)
    if emit:
        emit({"stage": "reference", "file": rec["reference_path"]})
    ref = analyze_file(rec["reference_path"], config=cfg, emit=emit)
    style = build_style_profile(rec["reference_path"], config=cfg, analysis=ref)
    save_profile(style, project_dir(project_id, cfg) / "style_profile.json")
    return {"clips": clips, "reference": ref, "style": style}


def load_style(project_id: str, cfg: AppConfig | None = None) -> dict[str, Any] | None:
    p = project_dir(project_id, cfg) / "style_profile.json"
    if p.is_file():
        return json.loads(p.read_text())
    return None


def patch_edl(
    project_id: str,
    *,
    op: str,
    segment_id: str,
    in_s: float | None = None,
    out_s: float | None = None,
    cfg: AppConfig | None = None,
) -> EDL:
    cfg = cfg or load_config()
    edl = load_edl(project_id, cfg)
    if not edl:
        raise KeyError("no edl")
    segs = list(edl.segments)
    idx = next((i for i, s in enumerate(segs) if s.id == segment_id), None)
    if idx is None:
        raise KeyError(segment_id)
    seg = segs[idx]
    if op == "remove":
        segs.pop(idx)
    elif op == "lock":
        segs[idx] = seg.model_copy(update={"locked": True})
    elif op == "unlock":
        segs[idx] = seg.model_copy(update={"locked": False})
    elif op == "nudge":
        analyses = load_analyses_for_project(project_id, cfg)
        new_in = seg.in_s if in_s is None else in_s
        new_out = seg.out_s if out_s is None else out_s
        from ave.heuristic.assembler import snap_to_boundary_values

        shot = _shot_for(analyses, seg)
        if shot:
            new_in = snap_to_boundary_values(shot, new_in)
            new_out = snap_to_boundary_values(shot, new_out)
        segs[idx] = seg.model_copy(update={"in_s": new_in, "out_s": new_out})
    else:
        raise ValueError(op)
    for i, s in enumerate(segs):
        segs[i] = s.model_copy(update={"id": s.id})
    updated = edl.model_copy(update={"segments": segs})
    analyses = load_analyses_for_project(project_id, cfg)
    result = validate_edl(updated, index_from_analyses(analyses), check_target=False)
    if not result.ok:
        raise ValueError(result.model_dump_json())
    save_edl(project_id, updated, cfg)
    return updated


def _shot_for(analyses: list[dict[str, Any]], seg: Segment) -> dict[str, Any] | None:
    for a in analyses:
        if Path(a["path"]).name != Path(seg.source).name and a["path"] != seg.source:
            continue
        for s in a.get("shots") or []:
            item = dict(s)
            item["words"] = a.get("transcript", {}).get("words") or []
            item["vad"] = a.get("vad") or {}
            if s["in_s"] - 0.05 <= seg.in_s and s["out_s"] + 0.05 >= seg.out_s:
                return item
        if a.get("shots"):
            item = dict(a["shots"][0])
            item["words"] = a.get("transcript", {}).get("words") or []
            item["vad"] = a.get("vad") or {}
            return item
    return None
