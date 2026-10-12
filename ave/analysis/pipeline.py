from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ave.analysis.hashing import file_hash, fingerprint
from ave.analysis.probe import list_media, probe_file
from ave.analysis.proxy import make_proxy
from ave.analysis.shots import detect_shots
from ave.analysis.timestamps import shot_timestamp_iso
from ave.config import AppConfig, load_config
from ave.db import connect, get_asset, get_asset_by_hash, upsert_asset
from ave.ffmpeg import FFmpegError

Emit = Callable[[dict[str, Any]], None]


def analyze_folder(
    folder: str | Path,
    *,
    config: AppConfig | None = None,
    emit: Emit | None = None,
) -> list[dict[str, Any]]:
    cfg = config or load_config()
    folder = Path(folder).resolve()
    files = list_media(folder)
    results = []
    for i, path in enumerate(files):
        if emit:
            emit({"stage": "analyze", "file": str(path), "index": i, "total": len(files)})
        try:
            results.append(analyze_file(path, config=cfg, emit=emit))
        except FFmpegError as exc:
            if emit:
                emit({"stage": "error", "file": str(path), "error": str(exc)})
            results.append({"path": str(path), "error": str(exc), "status": "error"})
    return results


def analyze_file(
    path: str | Path,
    *,
    config: AppConfig | None = None,
    emit: Emit | None = None,
    force: bool = False,
) -> dict[str, Any]:
    cfg = config or load_config()
    path = Path(path).resolve()
    conn = connect(cfg.paths.cache / "ave.sqlite")
    size, mtime = fingerprint(path)
    existing = get_asset(conn, str(path))
    if (
        not force
        and existing
        and existing.get("status") == "complete"
        and existing.get("size") == size
        and existing.get("mtime") == mtime
        and existing.get("analysis_path")
        and Path(existing["analysis_path"]).is_file()
    ):
        return json.loads(Path(existing["analysis_path"]).read_text())

    digest = file_hash(path)
    hashed = get_asset_by_hash(conn, digest)
    if not force and hashed and hashed.get("analysis_path") and Path(hashed["analysis_path"]).is_file():
        data = json.loads(Path(hashed["analysis_path"]).read_text())
        data["path"] = str(path)
        dest = _asset_dir(cfg, digest) / "analysis.json"
        dest.write_text(json.dumps(data, indent=2))
        _store(conn, path, digest, size, mtime, data, dest, "complete", None)
        return data

    asset_dir = _asset_dir(cfg, digest)
    dest = asset_dir / "analysis.json"
    data: dict[str, Any] = {"version": 1, "path": str(path), "file_hash": digest, "status": "running"}

    def _save() -> None:
        dest.write_text(json.dumps(data, indent=2))

    if emit:
        emit({"stage": "probe", "file": str(path)})
    data["probe"] = probe_file(path)
    data["shot_at"] = shot_timestamp_iso(path, data["probe"])
    _save()

    proxy_path = asset_dir / "proxy.mp4"
    if not proxy_path.is_file():
        if emit:
            emit({"stage": "proxy", "file": str(path)})
        fps = data["probe"].get("avg_fps") or data["probe"].get("fps") or None
        if data["probe"].get("is_vfr"):
            fps = round(fps or 30)
        make_proxy(path, proxy_path, height=cfg.render.preview_height, fps=fps, config=cfg)
    data["proxy_path"] = str(proxy_path)
    _save()

    video_src = proxy_path if proxy_path.is_file() else path
    if emit:
        emit({"stage": "shots", "file": str(path)})
    shots = detect_shots(
        video_src,
        min_shot_s=cfg.analysis.min_shot_s,
        threshold=cfg.analysis.scene_threshold,
    )
    data["shots"] = shots
    _save()

    if emit:
        emit({"stage": "vad", "file": str(path)})
    from ave.analysis.vad import detect_voice

    data["vad"] = detect_voice(path, threshold=cfg.analysis.vad_threshold)
    _save()

    if emit:
        emit({"stage": "transcribe", "file": str(path)})
    from ave.analysis.transcribe import transcribe

    data["transcript"] = transcribe(path, model=cfg.analysis.whisper_model)
    _save()

    from ave.analysis.captions import caption_shot
    from ave.analysis.embeddings import embed_shot
    from ave.analysis.loudness import shot_loudness
    from ave.analysis.quality import score_shot

    for i, shot in enumerate(data["shots"]):
        if emit:
            emit(
                {
                    "stage": "shot",
                    "file": str(path),
                    "index": i,
                    "total": len(data["shots"]),
                    "shot_id": shot["id"],
                }
            )
        in_s, out_s = shot["in_s"], shot["out_s"]
        shot["quality"] = score_shot(video_src, in_s, out_s)
        shot["loudness_lufs"] = shot_loudness(path, in_s, out_s)
        shot["speech_share"] = _speech_share(data["vad"], in_s, out_s)
        shot["role_hint"] = "a_roll" if shot["speech_share"] >= 0.3 else "b_roll"
        shot["captions"] = caption_shot(video_src, in_s, out_s, config=cfg)
        times = [c["t"] for c in shot["captions"]]
        shot["embedding"] = embed_shot(video_src, times)
        _save()

    data["status"] = "complete"
    _save()
    _store(conn, path, digest, size, mtime, data, dest, "complete", None)
    return data


def load_analysis(path: Path, config: AppConfig | None = None) -> dict[str, Any] | None:
    cfg = config or load_config()
    conn = connect(cfg.paths.cache / "ave.sqlite")
    row = get_asset(conn, str(path.resolve()))
    if row and row.get("analysis_path") and Path(row["analysis_path"]).is_file():
        return json.loads(Path(row["analysis_path"]).read_text())
    return None


def _asset_dir(cfg: AppConfig, digest: str) -> Path:
    d = cfg.paths.cache / "assets" / digest
    d.mkdir(parents=True, exist_ok=True)
    return d


def _store(conn, path, digest, size, mtime, data, dest, status, error) -> None:
    probe = data.get("probe") or {}
    upsert_asset(
        conn,
        path=str(path),
        file_hash=digest,
        size=size,
        mtime=mtime,
        duration_s=probe.get("duration_s"),
        width=probe.get("width"),
        height=probe.get("height"),
        fps=probe.get("fps"),
        shot_at=data.get("shot_at"),
        analysis_path=str(dest),
        status=status,
        error=error,
    )


def _speech_share(vad: dict[str, Any], in_s: float, out_s: float) -> float:
    dur = max(out_s - in_s, 1e-6)
    spoken = 0.0
    for r in vad.get("speech") or []:
        a, b = max(in_s, r["start"]), min(out_s, r["end"])
        if b > a:
            spoken += b - a
    return spoken / dur
