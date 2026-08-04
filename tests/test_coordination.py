"""Coordination — depth classifier + shared activity."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def coord_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import mag.coordination as c

    act = tmp_path / "state" / "shared_activity.jsonl"
    act.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(c, "ACTIVITY_PATH", act)
    monkeypatch.setattr(c, "STATE_DIR", tmp_path / "state")
    return act


def test_classify_depth_overview():
    from mag.coordination import classify_depth

    r = classify_depth("Give me a big picture interlink map of the ecosystem")
    assert r["depth"] == "overview"
    assert r["seat"] == "grok_tui"
    assert r["launch"] is False


def test_classify_depth_heavy():
    from mag.coordination import classify_depth

    r = classify_depth("Implement multi-file refactor for orchestrator queue drain")
    assert r["depth"] == "heavy_code"
    assert r["seat"] == "deepseek"


def test_classify_depth_simple():
    from mag.coordination import classify_depth

    r = classify_depth("fix typo in one file")
    assert r["depth"] == "simple_code"
    assert r["seat"] == "local"


def test_classify_depth_scut():
    from mag.coordination import classify_depth

    r = classify_depth("doctor health status")
    assert r["depth"] == "scut"


def test_log_and_read_activity(coord_env):
    from mag.coordination import log_activity, read_activity, activity_summary

    log_activity(seat="deepseek", depth="heavy_code", goal="build tests", status="running")
    log_activity(seat="cursor", depth="simple_code", goal="fix lint", status="done")
    rows = read_activity(limit=10)
    assert len(rows) == 2
    assert rows[0]["seat"] == "cursor"
    summary = activity_summary(limit=10)
    assert summary["ok"] is True
    assert summary["running_n"] >= 0


def test_coordinate_plan_only(coord_env, monkeypatch: pytest.MonkeyPatch):
    from mag.coordination import coordinate

    monkeypatch.setattr(
        "mag.context_pack.build_context_pack",
        lambda **kw: {"ts": "t", "brief": "b"},
    )
    monkeypatch.setattr(
        "mag.context_pack.format_context_pack_text",
        lambda p, **kw: "# pack",
    )
    res = coordinate("Plan the architecture for republic launch", launch=True)
    assert res["ok"] is True
    assert res["action"] == "file_for_grok"
    assert res["launched"] is False


def test_coordinate_dry_classify(coord_env):
    from mag.coordination import coordinate

    res = coordinate("list open loops", launch=False)
    assert res["ok"] is True
    assert res["action"] == "classified_only"
    assert res["classification"]["depth"] == "scut"


def test_rest_coordination_smoke():
    from dashboard.rest import h_coordination, h_coordinate

    code, body = h_coordination({}, None)
    assert code == 200
    assert body.get("ok") is True

    code2, body2 = h_coordinate({}, {"goal": "status check", "launch": False})
    assert code2 == 200
    assert body2.get("ok") is True
