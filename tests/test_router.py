"""Unified router — one classifier, honest failures."""
from __future__ import annotations

import pytest


def test_route_scut_local():
    from mag.router import route

    r = route("doctor health status")
    assert r["depth"] == "scut"
    assert r["seat"] == "local"
    assert r["provider"] == "ollama"
    assert r["executable"] is True
    assert r["ok"] is True


def test_route_simple_typo_local():
    from mag.router import route

    r = route("fix typo in README one file")
    assert r["depth"] == "simple_code"
    assert r["seat"] == "local"
    assert r["executable"] is True


def test_route_overview_grok_pack_only():
    from mag.router import route

    r = route("big picture interlink map of the ecosystem")
    assert r["depth"] == "overview"
    assert r["seat"] == "grok_tui"
    assert r["launch"] is False
    assert r["executable"] is False
    assert r["provider"] is None
    assert r["ok"] is True


def test_route_overview_never_ollama():
    from mag.router import route

    r = route("Give me a big picture interlink map of the ecosystem")
    assert r["provider"] != "ollama"
    assert r["seat"] == "grok_tui"


def test_route_heavy_without_keys_fails_loud(monkeypatch):
    from mag.router import route

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_OVERMIND_API_KEY", raising=False)
    r = route("implement multi-file orchestrator heal loop with tests")
    assert r["depth"] == "heavy_code"
    if not r.get("executable"):
        assert r["ok"] is False
        assert r["error"] == "no_execution_provider"


def test_route_cursor_marker():
    from mag.router import route

    r = route("via cursor implement seat identity in mag/seats.py")
    assert r["seat"] == "cursor"
    assert r["executable"] is False
    assert r["mode"] == "defer_cursor"


def test_classifiers_agree():
    from mag.coordination import classify_depth
    from mag.dispatch import _classify_job
    from mag.router import route

    goals = [
        "doctor health status",
        "fix typo in README",
        "implement multi-file refactor",
        "big picture ecosystem map",
        "via cursor wire dashboard",
    ]
    for g in goals:
        rt = route(g)
        cd = classify_depth(g)
        assert rt["depth"] == cd["depth"], f"depth mismatch for {g!r}"


def test_activity_dedupes_stale_running(tmp_path, monkeypatch):
    import mag.coordination as c

    act = tmp_path / "state" / "shared_activity.jsonl"
    act.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(c, "ACTIVITY_PATH", act)
    aid = "act-test-1"
    c.log_activity(seat="local", depth="scut", goal="task", status="running", activity_id=aid)
    c.log_activity(seat="local", depth="scut", goal="task", status="done", activity_id=aid)
    rows = c.read_activity(limit=10)
    assert len(rows) == 1
    assert rows[0]["status"] == "done"
    summary = c.activity_summary(limit=10)
    assert summary["running_n"] == 0


def test_rest_route_smoke():
    from dashboard.rest import h_route

    code, body = h_route({}, {"goal": "doctor health", "launch": False})
    assert code == 200
    assert body.get("ok") is True
    assert body.get("schema") == "mag_intent.v1"
    assert (body.get("decision") or {}).get("route")
