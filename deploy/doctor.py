"""Check the local-first stack and print the fix for anything missing.

`make doctor` runs this. It never starts services and never downloads models.
Exit 0 when Docker, Compose, Model Runner, disk, and memory all pass.
Exit 1 when a required check fails. A missing model pull is a warning, not a
failure: the first `make up` downloads it and the UI shows that as a job.
"""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass


MIN_COMPOSE = (2, 35, 0)
MIN_DISK_GB = 20.0
MIN_MEMORY_GB = 16.0


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""
    required: bool = True


def _run(cmd: list[str], timeout: float = 8.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _version_tuple(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not match:
        return ()
    return tuple(int(p) for p in match.groups() if p is not None)


def check_docker() -> Check:
    if not shutil.which("docker"):
        return Check(
            "docker",
            False,
            "docker is not on PATH",
            "Install Docker Desktop for Apple Silicon: https://docs.docker.com/desktop/setup/install/mac-install/",
        )
    try:
        proc = _run(["docker", "info", "--format", "{{.ServerVersion}} {{.OperatingSystem}}"])
    except subprocess.TimeoutExpired:
        return Check("docker", False, "docker info timed out", "Start Docker Desktop and wait until the engine is running.")
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "docker info failed").strip().splitlines()[-1]
        return Check("docker", False, err, "Start Docker Desktop. On a Mac, the engine must be running before make up.")
    return Check("docker", True, (proc.stdout or "running").strip())


def check_compose() -> Check:
    try:
        proc = _run(["docker", "compose", "version", "--short"])
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return Check("compose", False, "docker compose is missing", "Update Docker Desktop. Compose v2.35+ is required for models:.")
    version = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0 or not version:
        return Check("compose", False, "docker compose version failed", "Update Docker Desktop so the Compose plugin is installed.")
    parsed = _version_tuple(version)
    if parsed and parsed < MIN_COMPOSE:
        return Check(
            "compose",
            False,
            f"Compose {version} is older than 2.35",
            "Update Docker Desktop. Model Runner services need Compose v2.35 or newer.",
        )
    return Check("compose", True, version or "present")


def check_model_runner() -> Check:
    if not shutil.which("docker"):
        return Check("model-runner", False, "skipped because docker is missing", "Install Docker Desktop, then enable Model Runner in Settings → AI.")
    try:
        proc = _run(["docker", "model", "status"])
    except subprocess.TimeoutExpired:
        return Check("model-runner", False, "docker model status timed out", "Enable Model Runner in Docker Desktop → Settings → AI, then retry.")
    text = f"{proc.stdout}\n{proc.stderr}".strip()
    if proc.returncode != 0 or "not a docker command" in text:
        return Check(
            "model-runner",
            False,
            "docker model is not available",
            "Enable Model Runner in Docker Desktop → Settings → AI. If the CLI still cannot see it: "
            "ln -s /Applications/Docker.app/Contents/Resources/cli-plugins/docker-model ~/.docker/cli-plugins/docker-model",
        )
    enabled = "disabled" not in text.lower()
    return Check(
        "model-runner",
        enabled,
        text.splitlines()[0] if text else "available",
        "" if enabled else "Enable Model Runner in Docker Desktop → Settings → AI. It runs llama.cpp on the Mac GPU, outside the VM.",
    )


def check_disk() -> Check:
    usage = shutil.disk_usage(Path_cwd())
    free_gb = usage.free / (1024**3)
    ok = free_gb >= MIN_DISK_GB
    return Check(
        "disk",
        ok,
        f"{free_gb:.1f} GB free (need {MIN_MEMORY_GB and MIN_DISK_GB:.0f} GB for models and proxies)",
        "" if ok else "Free at least 20 GB. Models and proxy files land in the Docker cache and EXPORT_DIR.",
    )


def Path_cwd():
    from pathlib import Path

    return Path(".").resolve()


def check_memory() -> Check:
    gb = _memory_gb()
    if gb is None:
        return Check("memory", False, "could not read physical memory", "Confirm this Mac has at least 16 GB. The target machine is an M3 Pro with 18 GB.")
    ok = gb >= MIN_MEMORY_GB
    return Check(
        "memory",
        ok,
        f"{gb:.1f} GB",
        "" if ok else "This stack targets 18 GB unified memory. Close other apps or use a machine with at least 16 GB.",
    )


def _memory_gb() -> float | None:
    if platform.system() == "Darwin":
        try:
            out = _run(["sysctl", "-n", "hw.memsize"])
            return int(out.stdout.strip()) / (1024**3)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            return None
    try:
        import os

        return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / (1024**3)
    except (ValueError, OSError):
        return None


def check_models() -> Check:
    if not shutil.which("docker"):
        return Check("models", False, "skipped because docker is missing", required=False)
    try:
        proc = _run(["docker", "model", "ls"])
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return Check("models", False, "could not list models", "Run make doctor after Model Runner is enabled.", required=False)
    text = proc.stdout or ""
    names = [line.split()[0] for line in text.splitlines()[1:] if line.strip()]
    if not names:
        return Check(
            "models",
            False,
            "no local models yet",
            "The first make up pulls ai/qwen2.5:7B-Q4_K_M and the vision model. "
            "That download is a job with progress, not a doctor failure. "
            "Free more than 20 GB first: a 7B Q4 model is about 4.7 GB.",
            required=False,
        )
    return Check("models", True, ", ".join(names), required=False)


def run_checks() -> list[Check]:
    return [check_docker(), check_compose(), check_model_runner(), check_disk(), check_memory(), check_models()]


def main() -> int:
    as_json = "--json" in sys.argv
    checks = run_checks()
    failed = [c for c in checks if not c.ok and c.required]
    warnings = [c for c in checks if not c.ok and not c.required]
    if as_json:
        print(json.dumps([c.__dict__ for c in checks], indent=2))
    else:
        for check in checks:
            mark = "ok" if check.ok else ("warn" if not check.required else "FAIL")
            print(f"[{mark}] {check.name}: {check.detail}")
            if not check.ok and check.fix:
                print(f"       fix: {check.fix}")
        if failed:
            print(f"\n{len(failed)} check(s) failed. make up will not bring the stack up green until these pass.")
        elif warnings:
            print(f"\nRequired checks passed. {len(warnings)} warning(s). Run make up, then open http://127.0.0.1:3000")
        else:
            print("\nAll checks passed. Run make up, then open http://127.0.0.1:3000")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
