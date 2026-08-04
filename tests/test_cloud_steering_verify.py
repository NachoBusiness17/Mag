"""Tests for cloud steering home verify."""
from __future__ import annotations

from unittest.mock import patch

from mag import cloud_steering_verify as csv


def test_cursor_secrets_block():
    block = csv.cursor_secrets_block("http://100.1.2.3:8765", "sekrit")
    assert "MAG_PUBLIC_URL=http://100.1.2.3:8765" in block
    assert "MAG_REMOTE_TOKEN=sekrit" in block
    assert "cursor_bridge.py status" in block


def test_suggest_public_urls_includes_tailscale(monkeypatch):
    monkeypatch.setattr(csv, "_tailscale_ipv4", lambda: "100.64.0.1")
    monkeypatch.setattr(csv, "_lan_ipv4_candidates", lambda: ["192.168.1.10"])
    urls = csv.suggest_public_urls(8765)
    assert urls[0] == "http://100.64.0.1:8765"
    assert "http://192.168.1.10:8765" in urls


def test_verify_home_local_down(monkeypatch):
    monkeypatch.setattr(csv, "_probe_url", lambda *a, **k: {"reachable": False})
    monkeypatch.setattr(
        "mag.distributed_surface.auth_status",
        lambda: {"token_configured": False, "remote_bind": False},
    )
    monkeypatch.setattr("mag.distributed_surface.is_remote_bind", lambda: False)
    monkeypatch.setattr("mag.distributed_surface.remote_token", lambda: "")
    monkeypatch.setattr("mag.distributed_surface.surface_status", lambda: {"ok": True})
    monkeypatch.setattr(csv, "suggest_public_urls", lambda port=8765: [])

    report = csv.verify_home(probe_remote=False)
    assert report["ok"] is False
    assert any("FAIL" in c for c in report["checks"])
