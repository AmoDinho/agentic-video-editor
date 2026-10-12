from __future__ import annotations

import hashlib
from pathlib import Path


def file_hash(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def fingerprint(path: Path) -> tuple[int, float]:
    st = path.stat()
    return st.st_size, st.st_mtime
