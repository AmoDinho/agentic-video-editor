from __future__ import annotations

from pathlib import Path

from ave.analysis.pipeline import analyze_file
from ave.config import AppConfig
from ave.heuristic.assembler import assemble
from ave.style.profile import build_style_profile


def test_assemble_watchable(samples: dict[str, Path], tmp_path: Path):
    cfg = AppConfig()
    cfg.paths.cache_dir = str(tmp_path / "cache")
    cfg.paths.projects_dir = str(tmp_path / "projects")
    analyses = [
        analyze_file(samples["clip_24"], config=cfg),
        analyze_file(samples["clip_30"], config=cfg),
        analyze_file(samples["clip_25"], config=cfg),
    ]
    style = build_style_profile(samples["vlog"], config=cfg)
    edl = assemble(analyses, style, project_id="t", target_duration_s=8)
    assert edl.segments
    assert all(s.reason for s in edl.segments)
    assert all(s.duration_s >= 0.3 for s in edl.segments)
    assert edl.duration_s > 0
