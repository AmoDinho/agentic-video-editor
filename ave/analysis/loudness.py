from __future__ import annotations

import re
from pathlib import Path


def shot_loudness(path: Path, in_s: float, out_s: float) -> float | None:
    from ave.ffmpeg import run

    result = run(
        [
            "-ss",
            f"{in_s:.4f}",
            "-to",
            f"{out_s:.4f}",
            "-i",
            str(path),
            "-af",
            "ebur128=framelog=verbose",
            "-f",
            "null",
            "-",
        ],
        check=False,
        timeout=300,
    )
    integrated = None
    for line in (result.stderr or "").splitlines():
        if "I:" in line and "LUFS" in line:
            m = re.search(r"I:\s*(-?[0-9.]+)", line)
            if m:
                try:
                    integrated = float(m.group(1))
                except ValueError:
                    continue
    return integrated
