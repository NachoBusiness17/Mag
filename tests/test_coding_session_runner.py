"""Tests for mag/coding_session_runner.py — run_until_done with mocked orchestrator."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.coding_session_loop import CONFIG_PATH, load_config  # noqa: E402
from mag.coding_session_runner import build_run_report, run_until_done  # noqa: E402


def _cfg():
    cfg = dict(load_config(CONFIG_PATH))
    gates = cfg.get("gates") or {}
    pre = [g for g in gates.get("preflight") or [] if g.get("id") != "ui_smoke"]
    cfg["gates"] = {"preflight": pre, "session_done": gates.get("session_done") or []}
    cfg["bead_on_close"] = False
    return cfg


def test_run_until_done_preflight_fail(monkeypatch, tmp_path):
    report_dir = tmp_path / "memory" / "runs" / "coding_session_run"
    monkeypatch.setattr("mag.coding_session_runner.RUN_REPORT_DIR", report_dir)
    monkeypatch.setattr(
        "mag.coding_session_runner.run_preflight",
        lambda **_: {"ok": False, "preflight": [{"id": "x", "pass": False}]},
    )

    out = run_until_done(config=_cfg(), max_ticks=3)
    assert out.get("ok") is False
    assert out.get("phase") == "preflight_fail"
    assert out.get("ticks") == 0
    assert out.get("report_path")
    assert report_dir.is_dir()
    reports = list(report_dir.glob("*.json"))
    assert len(reports) == 1
    saved = json.loads(reports[0].read_text(encoding="utf-8"))
    assert saved.get("phase") == "preflight_fail"


def test_run_until_done_closed(monkeypatch, tmp_path):
    report_dir = tmp_path / "memory" / "runs" / "coding_session_run"
    monkeypatch.setattr("mag.coding_session_runner.RUN_REPORT_DIR", report_dir)
    monkeypatch.setattr(
        "mag.coding_session_runner.run_preflight",
        lambda **_: {"ok": True, "passed": 1, "total": 1},
    )
    monkeypatch.setattr(
        "mag.coding_session_runner.session_status",
        lambda **_: {"ok": True, "state": {"seeded_ts": "2026-01-01T00:00:00+00:00"}},
    )
    monkeypatch.setattr("mag.coding_session_runner.seed_desk", lambda **_: {"ok": True})
    monkeypatch.setattr("mag.coding_session_orchestrator.plan_session", lambda **_: {"ok": True})

    tick_n = {"n": 0}

    def fake_tick(**kwargs):
        tick_n["n"] += 1
        return {
            "ok": True,
            "active_sprint": "sprint_1",
            "advance": {
                "status": {
                    "active_sprint": "sprint_1",
                    "completed_sprints": ["sprint_0"],
                    "all_sprints_done": True,
                }
            },
            "close": {"closed": True, "reason": "closed", "session_id": "test-session"},
        }

    monkeypatch.setattr("mag.coding_session_orchestrator.orchestrator_tick", fake_tick)

    cfg = _cfg()
    cfg["session_id"] = "test-closed"
    out = run_until_done(config=cfg, max_ticks=10)
    assert out.get("ok") is True
    assert out.get("phase") == "closed"
    assert out.get("ticks") == 1
    assert (out.get("close") or {}).get("closed") is True
    assert out.get("report", {}).get("phase") == "closed"


def test_run_until_done_already_closed(monkeypatch, tmp_path):
    report_dir = tmp_path / "memory" / "runs" / "coding_session_run"
    monkeypatch.setattr("mag.coding_session_runner.RUN_REPORT_DIR", report_dir)
    monkeypatch.setattr(
        "mag.coding_session_runner.run_preflight",
        lambda **_: {"ok": True, "passed": 1, "total": 1},
    )
    monkeypatch.setattr(
        "mag.coding_session_runner.session_status",
        lambda **_: {
            "ok": True,
            "has_done": True,
            "state": {"seeded_ts": "2026-01-01T00:00:00+00:00", "status": "closed"},
            "session_done_gates": [{"id": "g1", "pass": True}],
        },
    )
    monkeypatch.setattr("mag.coding_session_runner.seed_desk", lambda **_: {"ok": True})
    monkeypatch.setattr("mag.coding_session_orchestrator.plan_session", lambda **_: {"ok": True})
    monkeypatch.setattr(
        "mag.coding_session_runner.close_session_if_ready",
        lambda **_: {"ok": True, "closed": True, "reason": "already_closed"},
    )
    def _no_tick(**_):
        raise AssertionError("should not tick")

    monkeypatch.setattr("mag.coding_session_orchestrator.orchestrator_tick", _no_tick)

    cfg = _cfg()
    cfg["session_id"] = "test-already-closed"
    out = run_until_done(config=cfg, max_ticks=50)
    assert out.get("ok") is True
    assert out.get("phase") == "closed"
    assert out.get("reason") == "already_closed"
    assert out.get("ticks") == 0


def test_run_until_done_force_new_seed_reopens(monkeypatch, tmp_path):
    report_dir = tmp_path / "memory" / "runs" / "coding_session_run"
    monkeypatch.setattr("mag.coding_session_runner.RUN_REPORT_DIR", report_dir)
    monkeypatch.setattr(
        "mag.coding_session_runner.run_preflight",
        lambda **_: {"ok": True, "passed": 1, "total": 1},
    )
    calls = {"seed": 0}

    def _status(**_):
        if calls["seed"] == 0:
            return {
                "ok": True,
                "has_done": False,
                "state": {"seeded_ts": "2026-01-01T00:00:00+00:00", "status": "closed"},
                "session_done_gates": [{"id": "g1", "pass": False}],
            }
        return {
            "ok": True,
            "has_done": False,
            "state": {"seeded_ts": "2026-01-02T00:00:00+00:00", "status": "ready"},
            "session_done_gates": [{"id": "g1", "pass": False}],
        }

    monkeypatch.setattr("mag.coding_session_runner.session_status", _status)

    def _seed(**_):
        calls["seed"] += 1
        return {"ok": True}

    monkeypatch.setattr("mag.coding_session_runner.seed_desk", _seed)
    monkeypatch.setattr("mag.coding_session_orchestrator.plan_session", lambda **_: {"ok": True})
    monkeypatch.setattr(
        "mag.coding_session_orchestrator.orchestrator_tick",
        lambda **_: {"ok": True, "recommended_action": "hold", "progress_key": "a"},
    )
    monkeypatch.setattr(
        "mag.coding_session_runner.close_session_if_ready",
        lambda **_: {"ok": True, "closed": False},
    )

    cfg = _cfg()
    cfg["session_id"] = "test-force-seed"
    out = run_until_done(config=cfg, max_ticks=1, force_new_seed=True)
    assert calls["seed"] == 1
    assert out.get("ticks") == 1


def test_run_until_done_stalled(monkeypatch, tmp_path):
    report_dir = tmp_path / "memory" / "runs" / "coding_session_run"
    monkeypatch.setattr("mag.coding_session_runner.RUN_REPORT_DIR", report_dir)
    monkeypatch.setattr(
        "mag.coding_session_runner.run_preflight",
        lambda **_: {"ok": True, "passed": 1, "total": 1},
    )
    monkeypatch.setattr(
        "mag.coding_session_runner.session_status",
        lambda **_: {"ok": True, "state": {"seeded_ts": "2026-01-01T00:00:00+00:00"}},
    )
    monkeypatch.setattr("mag.coding_session_runner.seed_desk", lambda **_: {"ok": True})
    monkeypatch.setattr("mag.coding_session_orchestrator.plan_session", lambda **_: {"ok": True})
    monkeypatch.setattr(
        "mag.coding_session_runner.close_session_if_ready",
        lambda **_: {"ok": True, "closed": False, "reason": "session_done_gates_open"},
    )

    stagnant = {
        "ok": True,
        "active_sprint": "sprint_2",
        "advance": {
            "status": {
                "active_sprint": "sprint_2",
                "completed_sprints": ["sprint_0"],
                "all_sprints_done": False,
            }
        },
        "step": {"acted": {"ok": False}},
    }
    monkeypatch.setattr(
        "mag.coding_session_orchestrator.orchestrator_tick",
        lambda **_: dict(stagnant),
    )

    cfg = _cfg()
    cfg["session_id"] = "test-stalled"
    out = run_until_done(config=cfg, max_ticks=20, stall_ticks=3)
    assert out.get("ok") is True
    assert out.get("phase") == "stalled"
    assert out.get("reason") == "no_progress"
    assert out.get("ticks") >= 3


def test_build_run_report_includes_gates_and_artifacts(monkeypatch, tmp_path):
    factory = tmp_path / "memory" / "factory"
    factory.mkdir(parents=True)
    audit = factory / "build_audit-test.json"
    audit.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("mag.coding_session_runner.ROOT", tmp_path)
    monkeypatch.setattr(
        "mag.coding_session_runner.session_status",
        lambda **_: {"session_done_gates": [{"id": "build_audit_module", "pass": True}]},
    )
    monkeypatch.setattr("mag.coding_session_runner._git_out", lambda *a: "main" if a[0] == "rev-parse" else "")
    monkeypatch.setattr("mag.env_registry.get_active_env", lambda: "operational")

    cfg = _cfg()
    report = build_run_report(
        phase="closed",
        session_id="test-session",
        cfg=cfg,
        preflight={"ok": True},
        ticks=2,
    )
    assert report.get("phase") == "closed"
    assert report.get("branch") == "main"
    assert report.get("track") == "operational"
    assert report.get("build_audit_matches") == ["memory/factory/build_audit-test.json"]
    assert "review_artifacts" in report
