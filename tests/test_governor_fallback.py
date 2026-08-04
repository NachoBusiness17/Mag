"""Governor seat-dispatch provider policy: guard-stop -> retry ONCE on fallback.

Deferred decision from working.md 2026-08-03 14:06 incident (deepseek 3 empty
responses -> seat guard-stop -> nothing done). exec_queue_task must:
- mark done ONLY on exit 0 AND no "Stopped:" guard phrase (anti-greenwash)
- retry ONCE on FALLBACK_PROVIDER (local ollama, T0-safe) when PRIMARY guard-stops
- NOT fall back on nonzero seat exit (seat-internal bug; provider can't fix it)
- leave the todo unchecked when both providers guard-stop
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mag.governor as g


def _task(title="some task", who="mag"):
    return {"id": "queue:0", "title": title, "value": 3,
            "blocked": False, "who": who, "exec": g.exec_queue_task}


def test_clean_primary_marks_done(monkeypatch):
    import mag.governor_autorun as ga

    monkeypatch.setattr(ga, "_drainer_active", lambda: False)
    monkeypatch.setattr(
        "mag.coordination.coordinate",
        lambda *a, **k: {"ok": False, "error": "mock-fail-to-seat"},
    )
    monkeypatch.setattr(
        ga,
        "route_task",
        lambda goal, depth=None: {"depth": "simple_code", "provider": "deepseek", "mode": "dispatch"},
    )
    calls = []
    monkeypatch.setattr(
        g, "_run_seat",
        lambda text, prov: (calls.append((text, prov)) or (0, "work done", "work done")),
    )
    marked = []
    monkeypatch.setattr(g, "_mark_queue_done", lambda title: marked.append(title))

    ok, detail = g.exec_queue_task(_task())

    assert ok and "exit=0" in detail
    assert len(calls) == 1 and calls[0][1] == "deepseek"
    assert marked == ["some task"]


def test_guard_stop_then_fallback_marks_done(monkeypatch):
    import mag.governor_autorun as ga

    monkeypatch.setattr(ga, "_drainer_active", lambda: False)
    monkeypatch.setattr(
        "mag.coordination.coordinate",
        lambda *a, **k: {"ok": False, "error": "mock-fail-to-seat"},
    )
    monkeypatch.setattr(
        ga,
        "route_task",
        lambda goal, depth=None: {"depth": "simple_code", "provider": "deepseek", "mode": "dispatch"},
    )
    calls = []

    def fake_run(text, prov):
        calls.append(prov)
        if len(calls) == 1:
            return 0, "Stopped: 3 consecutive empty model responses", \
                "Stopped: 3 consecutive empty model responses"
        return 0, "done on local", "done on local"

    monkeypatch.setattr(g, "_run_seat", fake_run)
    marked = []
    monkeypatch.setattr(g, "_mark_queue_done", lambda title: marked.append(title))

    ok, detail = g.exec_queue_task(_task())

    assert ok and "fallback" in detail and g.FALLBACK_PROVIDER in detail
    assert len(calls) == 2
    assert calls[0] == "deepseek" and calls[1] == g.FALLBACK_PROVIDER
    assert marked == ["some task"]


def test_both_guard_stop_not_marked(monkeypatch):
    import mag.governor_autorun as ga

    monkeypatch.setattr(ga, "_drainer_active", lambda: False)
    monkeypatch.setattr(
        "mag.coordination.coordinate",
        lambda *a, **k: {"ok": False, "error": "mock-fail-to-seat"},
    )
    monkeypatch.setattr(
        ga,
        "route_task",
        lambda goal, depth=None: {"depth": "simple_code", "provider": "deepseek", "mode": "dispatch"},
    )

    def fake_run(text, prov):
        return 0, "Stopped: context budget exhausted", "Stopped: context budget exhausted"

    monkeypatch.setattr(g, "_run_seat", fake_run)
    marked = []
    monkeypatch.setattr(g, "_mark_queue_done", lambda title: marked.append(title))

    ok, detail = g.exec_queue_task(_task())

    assert not ok and "guard-stop" in detail and "NOT marked done" in detail
    assert marked == []


def test_nonzero_exit_no_fallback(monkeypatch):
    import mag.governor_autorun as ga

    monkeypatch.setattr(ga, "_drainer_active", lambda: False)
    monkeypatch.setattr(
        "mag.coordination.coordinate",
        lambda *a, **k: {"ok": False, "error": "mock-fail-to-seat"},
    )
    monkeypatch.setattr(
        ga,
        "route_task",
        lambda goal, depth=None: {"depth": "simple_code", "provider": "deepseek", "mode": "dispatch"},
    )
    calls = []
    monkeypatch.setattr(
        g, "_run_seat",
        lambda text, prov: (calls.append(prov) or (7, "crash", "crash")),
    )
    marked = []
    monkeypatch.setattr(g, "_mark_queue_done", lambda title: marked.append(title))

    ok, detail = g.exec_queue_task(_task())

    assert not ok and "exit=7" in detail
    assert len(calls) == 1  # no fallback on seat-internal crash
    assert marked == []


def test_not_mag_skipped(monkeypatch):
    def boom(text, prov):
        raise AssertionError("seat must not run for non-mag tasks")

    monkeypatch.setattr(g, "_run_seat", boom)

    ok, detail = g.exec_queue_task(_task(who="operator"))

    assert not ok and "not assigned" in detail
