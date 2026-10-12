from __future__ import annotations

from pathlib import Path

from deploy.doctor import Check, check_disk, check_memory, run_checks
from deploy.media_mounts import mount_name, read_folders, render_override


def test_doctor_reports_a_fix_for_every_failure(monkeypatch):
    monkeypatch.setattr("deploy.doctor.shutil.which", lambda _name: None)
    checks = run_checks()
    failed = [c for c in checks if not c.ok]
    assert failed
    assert all(c.fix for c in failed if c.name in {"docker", "model-runner"})


def test_disk_and_memory_checks_return_checks():
    assert isinstance(check_disk(), Check)
    assert isinstance(check_memory(), Check)


def test_media_override_is_read_only(tmp_path: Path):
    listing = tmp_path / "media-folders.txt"
    listing.write_text("# comment\n\n~/Movies/Footage 2026\n/Volumes/T7/GoPro\n")
    folders = read_folders(listing)
    assert len(folders) == 2
    text = render_override(folders, "${EXPORT_DIR:-./exports}")
    assert ":ro" in text
    assert "/media/Footage-2026:ro" in text or "/media/Footage:ro" in text
    assert "worker:" in text
    used: set[str] = set()
    assert mount_name(Path("/a/GoPro"), used) == "GoPro"
    assert mount_name(Path("/b/GoPro"), used) == "GoPro-2"
