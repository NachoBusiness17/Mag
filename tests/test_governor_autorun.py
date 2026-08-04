"""Intelligent governor autorun: routing, fill, plan."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mag.governor as g
import mag.governor_autorun as ga


def _fake_route(goal, *, depth=None):
    return {
        "ok": True,
        "depth": "simple_code",
        "provider": "deepseek",
        "mode": "dispatch",
    }


def test_route_task_classifies_heavy():
    r = ga.route_task("Implement multi-file refactor for orchestrator queue drain")
    assert r["depth"] == "heavy_code"
    assert r["job"] == "hard_code"
    assert "cost_estimate" in r
    assert isinstance(r["skills"], list)


def test_route_task_scut():
    r = ga.route_task("doctor health status")
    assert r["depth"] == "scut"


def test_fill_queue_skips_duplicate(monkeypatch):
    monkeypatch.setattr(ga, "queue_has_goal", lambda goal: True)
    monkeypatch.setattr(
        "mag.autopilot._top_improve_candidates",
        lambda n: [{"claim": "test claim", "id": "c1", "score": 20}],
    )
    filled = ga.fill_queue(max_improve=1)
    assert filled["total_queued"] == 0
    assert filled["skipped"]


def test_exec_queue_task_uses_routed_provider(monkeypatch):
    monkeypatch.setattr(ga, "route_task", _fake_route)
    monkeypatch.setattr(ga, "_drainer_active", lambda: False)
    calls = []
    monkeypatch.setattr(
        g, "_run_seat",
        lambda text, prov: (calls.append((text, prov)) or (0, "work done", "work done")),
    )
    marked = []
    monkeypatch.setattr(g, "_mark_queue_done", lambda title: marked.append(title))

    ok, detail = g.exec_queue_task(
        {"id": "queue:0", "title": "some task", "who": "mag", "exec": g.exec_queue_task}
    )

    assert ok and "exit=0" in detail
    assert calls[0][1] == "deepseek"
    assert marked == ["some task"]


def test_guard_stop_fallback(monkeypatch):
    monkeypatch.setattr(ga, "route_task", _fake_route)
    monkeypatch.setattr(ga, "_drainer_active", lambda: False)
    calls = []

    def fake_run(text, prov):
        calls.append(prov)
        if len(calls) == 1:
            return 0, "Stopped: 3 consecutive empty model responses", "Stopped:"
        return 0, "done on local", "done on local"

    monkeypatch.setattr(g, "_run_seat", fake_run)
    marked = []
    monkeypatch.setattr(g, "_mark_queue_done", lambda title: marked.append(title))

    ok, detail = g.exec_queue_task(
        {"id": "queue:0", "title": "some task", "who": "mag", "exec": g.exec_queue_task}
    )

    assert ok and "fallback" in detail
    assert calls[1] == g.FALLBACK_PROVIDER
    assert marked == ["some task"]


def test_plan_pending_structure(monkeypatch):
    monkeypatch.setattr(ga, "route_task", _fake_route)
    plan = ga.plan_pending()
    assert plan["schema"] == "autorun_plan.v1"
    assert "orchestrator_queued" in plan
    assert "todo_mag" in plan


def test_autorun_once_dry(monkeypatch):
    monkeypatch.setattr(ga, "route_task", _fake_route)
    res = ga.autorun_once(fill=False, dry=True)
    assert res["action"] == "dry"
    assert "plan" in res
