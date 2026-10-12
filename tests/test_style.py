from __future__ import annotations

from pathlib import Path

from ave.analysis.pipeline import analyze_file
from ave.style.profile import build_style_profile


def test_vlog_vs_doc(samples: dict[str, Path], tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from ave.config import AppConfig

    cfg = AppConfig()
    cfg.paths.cache_dir = str(tmp_path / "cache")
    cfg.paths.projects_dir = str(tmp_path / "projects")
    vlog_a = analyze_file(samples["vlog"], config=cfg)
    doc_a = analyze_file(samples["doc"], config=cfg)
    vlog = build_style_profile(samples["vlog"], config=cfg, analysis=vlog_a)
    doc = build_style_profile(samples["doc"], config=cfg, analysis=doc_a)
    assert vlog["cuts_per_minute"] > doc["cuts_per_minute"]
    assert vlog["shot_length"]["median"] < doc["shot_length"]["median"]
    assert vlog["shot_count"] > doc["shot_count"]
