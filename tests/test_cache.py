from __future__ import annotations

import time
from pathlib import Path

from ave.analysis.pipeline import analyze_file
from ave.config import AppConfig


def test_rerun_is_fast(samples: dict[str, Path], tmp_path: Path):
    cfg = AppConfig()
    cfg.paths.cache_dir = str(tmp_path / "cache")
    cfg.paths.projects_dir = str(tmp_path / "projects")
    analyze_file(samples["clip_25"], config=cfg)
    t0 = time.perf_counter()
    again = analyze_file(samples["clip_25"], config=cfg)
    elapsed = time.perf_counter() - t0
    assert again.get("status") == "complete"
    assert elapsed < 2.0
