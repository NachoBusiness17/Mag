"""Decision framework + behavioral synth + loop escalation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def iso_env(tmp_path, monkeypatch):
    events = tmp_path / "behavioral_events.jsonl"
    decisions = tmp_path / "decisions_log.jsonl"
    daily = tmp_path / "improve" / "daily"
    daily.mkdir(parents=True)
    events.write_text(
        json.dumps({"kind": "collapse", "detail": "5x grep", "tool": "grep"}) + "\n",
        encoding="utf-8",
    )
    decisions.write_text(
        json.dumps({
            "context": "operator",
            "steer_input": "stop looping",
            "outcome": "collapse on grep",
        }) + "\n",
        encoding="utf-8",
    )
    import mag.decision_framework as df
    import mag.behavioral_synth as bs

    monkeypatch.setattr(df, "EVENTS_PATH", events)
    monkeypatch.setattr(df, "DECISIONS_PATH", decisions)
    monkeypatch.setattr(df, "BEHAVIORAL_DAILY", daily)
    monkeypatch.setattr(bs, "EVENTS_PATH", events)
    monkeypatch.setattr(bs, "DECISIONS_PATH", decisions)
    monkeypatch.setattr(bs, "DAILY_DIR", daily)
    yield tmp_path


def test_surface_tips(iso_env):
    from mag.decision_framework import surface_tips

    tips = surface_tips(goal="implement grep fix")
    assert tips
    assert any("collapse" in t.get("tip", "").lower() or t.get("id") == "event-collapse" for t in tips)


def test_decide_includes_route_and_interference(iso_env, monkeypatch):
    from mag.decision_framework import decide

    monkeypatch.setattr(
        "mag.operator_inbox.status",
        lambda: {"pending_n": 2},
    )
    d = decide("doctor health status")
    assert d["schema"] == "decision.v1"
    assert "route" in d
    assert d["interference"]["breadcrumbs_pending"] == 2


def test_escalate_on_loop_queues(monkeypatch):
    from mag.decision_framework import escalate_on_loop

    queued = []

    def fake_enqueue(goal, **kwargs):
        queued.append((goal, kwargs))
        return {"queue_id": "q-test"}

    monkeypatch.setattr("mag.orchestrator.enqueue", fake_enqueue)
    monkeypatch.setattr(
        "mag.operator_inbox.log_behavioral_event",
        lambda **kw: None,
    )
    monkeypatch.setattr("mag.compass.record_decision", lambda *a, **k: True)

    esc = escalate_on_loop(goal="fix seats.py", provider="ollama", tool="grep")
    assert esc["ok"]
    assert esc["target"] == "deepseek"
    assert esc.get("queue_id") == "q-test"
    assert queued


def test_synthesize_behavioral_leaf(iso_env):
    from mag.behavioral_synth import synthesize_behavioral_leaf

    r = synthesize_behavioral_leaf("2026-08-04")
    assert r["ok"]
    path = iso_env / "improve" / "daily" / "2026-08-04-behavioral.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "T1" in text
    assert "collapse" in text.lower()
