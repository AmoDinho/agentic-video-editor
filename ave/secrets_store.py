"""API keys encrypted in the local database.

The key that encrypts them is generated on first run and kept beside the
database, not in the repo. A saved key is shown masked. It is never returned
in full and never written to a log line.
"""

from __future__ import annotations

import base64
import hashlib
import os
import sqlite3
from pathlib import Path


def mask(key: str) -> str:
    if len(key) <= 8:
        return "·" * len(key)
    return f"{key[:6]}{'·' * 8}{key[-4:]}"


def save_key(db_path: Path, provider: str, key: str) -> str:
    secret = _secret(db_path.parent)
    conn = _connect(db_path)
    conn.execute(
        """INSERT INTO api_keys (provider, cipher) VALUES (?, ?)
           ON CONFLICT(provider) DO UPDATE SET cipher = excluded.cipher""",
        (provider, _encrypt(key, secret)),
    )
    conn.commit()
    return mask(key)


def load_key(db_path: Path, provider: str) -> str | None:
    env = os.environ.get(_env_name(provider))
    if env:
        return env
    conn = _connect(db_path)
    row = conn.execute("SELECT cipher FROM api_keys WHERE provider = ?", (provider,)).fetchone()
    if row is None:
        return None
    return _decrypt(row["cipher"], _secret(db_path.parent))


def masked(db_path: Path, provider: str) -> str | None:
    key = load_key(db_path, provider)
    return mask(key) if key else None


def cloud_preview(*, transcripts: int, descriptions: int, tokens_in: int, tokens_out: int) -> dict[str, object]:
    """What a cloud run is allowed to send. Video never appears here."""
    cost = (tokens_in * 0.000003) + (tokens_out * 0.000015)
    return {
        "sent": ["Transcripts", "Shot descriptions", "Timing and quality stats"],
        "never": ["Video and audio", "Keyframes and thumbnails", "File names and folders"],
        "counts": {"transcripts": transcripts, "descriptions": descriptions},
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "estimated_cost": round(cost, 2),
    }


def _env_name(provider: str) -> str:
    return {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}.get(provider, f"{provider.upper()}_API_KEY")


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS api_keys (provider TEXT PRIMARY KEY, cipher TEXT NOT NULL)")
    return conn


def _secret(directory: Path) -> bytes:
    path = directory / ".key"
    if path.is_file():
        return path.read_bytes()
    directory.mkdir(parents=True, exist_ok=True)
    secret = os.urandom(32)
    path.write_bytes(secret)
    path.chmod(0o600)
    return secret


def _encrypt(value: str, secret: bytes) -> str:
    raw = value.encode()
    stream = _stream(secret, len(raw))
    cipher = bytes(left ^ right for left, right in zip(raw, stream, strict=True))
    return base64.b64encode(cipher).decode()


def _decrypt(cipher: str, secret: bytes) -> str:
    raw = base64.b64decode(cipher)
    stream = _stream(secret, len(raw))
    return bytes(left ^ right for left, right in zip(raw, stream, strict=True)).decode()


def _stream(secret: bytes, length: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(secret + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:length]
