"""Optional native GPU sidecar for `make up-fast`.

Docker on a Mac cannot see the Apple GPU. This process runs on the host and
exposes mlx-whisper and CLIP at host.docker.internal:8077. CPU transcription
inside the worker remains the default. The sidecar is not required to edit.
"""

from __future__ import annotations

import os

from fastapi import FastAPI

app = FastAPI(title="AVE GPU sidecar")


@app.get("/health")
def health() -> dict[str, str]:
    return {"ok": "true", "mode": "native-gpu", "whisper": os.environ.get("WHISPER_MODEL", "small")}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("SIDECAR_PORT", "8077")))


if __name__ == "__main__":
    main()
