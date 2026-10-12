from __future__ import annotations

from fastapi.testclient import TestClient

from ave.api.app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["ffmpeg"]


def test_settings_and_projects():
    r = client.get("/settings")
    assert r.status_code == 200
    assert "llm" in r.json()
    r = client.get("/projects")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
