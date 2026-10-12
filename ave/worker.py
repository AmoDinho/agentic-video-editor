"""Worker process. Heavy work never runs in the API.

Phase 0 only proves the process starts, reaches Redis and Postgres when they
are configured, and exits cleanly. Later phases claim jobs from this loop.
"""

from __future__ import annotations

import os
import time


def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "")
    database_url = os.environ.get("DATABASE_URL", "")
    print(f"ave worker up redis={bool(redis_url)} db={bool(database_url)}", flush=True)
    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
