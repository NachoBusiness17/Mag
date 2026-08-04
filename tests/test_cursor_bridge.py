"""cursor_bridge — remote auth + steering probe."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


def test_mag_url_prefers_mag_url_over_public(monkeypatch):
    monkeypatch.setenv("MAG_URL", "http://home:8765")
    monkeypatch.setenv("MAG_PUBLIC_URL", "http://tailscale:8765")
    from watch import cursor_bridge as cb

    assert cb.mag_url() == "http://home:8765"


def test_mag_url_falls_back_to_public(monkeypatch):
    monkeypatch.delenv("MAG_URL", raising=False)
    monkeypatch.setenv("MAG_PUBLIC_URL", "http://tailscale:8765")
    from watch import cursor_bridge as cb

    assert cb.mag_url() == "http://tailscale:8765"


def test_auth_headers_includes_bearer(monkeypatch):
    monkeypatch.setenv("MAG_REMOTE_TOKEN", "sekrit")
    from watch import cursor_bridge as cb

    h = cb._auth_headers()
    assert h["Authorization"] == "Bearer sekrit"


def test_probe_hq_unreachable(monkeypatch):
    monkeypatch.delenv("MAG_URL", raising=False)
    monkeypatch.delenv("MAG_PUBLIC_URL", raising=False)
    from watch import cursor_bridge as cb

    def _boom(*_a, **_k):
        raise OSError("nope")

    with patch.object(cb.urllib.request, "urlopen", side_effect=_boom):
        st = cb.probe_hq()
    assert st["reachable"] is False
    assert "nope" in (st.get("error") or "")


def test_probe_hq_ok(monkeypatch):
    monkeypatch.setenv("MAG_URL", "http://127.0.0.1:8765")
    from watch import cursor_bridge as cb

    payload = json.dumps({"ok": True, "status": "up"}).encode()

    def _fake(_req, timeout=0):
        r = MagicMock()
        r.status = 200
        r.read.return_value = payload
        r.__enter__ = lambda s: s
        r.__exit__ = MagicMock(return_value=False)
        return r

    with patch.object(cb.urllib.request, "urlopen", side_effect=_fake):
        st = cb.probe_hq()
    assert st["reachable"] is True
    assert st["health"]["ok"] is True


def test_cmd_steer_unreachable_exits_2(monkeypatch, capsys):
    from watch import cursor_bridge as cb

    with patch.object(cb, "probe_hq", return_value={"reachable": False, "mag_url": "x", "error": "down"}):
        rc = cb.cmd_steer(
            "do thing",
            mode="delegate",
            seat="cursor-cloud",
            provider="deepseek",
            pack=False,
            background=False,
        )
    assert rc == 2
    out = json.loads(capsys.readouterr().out)
    assert out["steered"] is False
    assert out["fallback"] == "clone_or_handoff_when_home_up"
