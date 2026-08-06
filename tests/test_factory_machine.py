"""Tests for mag/factory_machine.py — retrospective writer + early paths (mock git)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.coding_session_loop import CONFIG_PATH, load_config  # noqa: E402
from mag import factory_machine as fm  # noqa: E402


def _cfg():
    cfg = dict(load_config(CONFIG_PATH))
    gates = cfg.get("gates") or {}
    pre = [g for g in gates.get("preflight") or [] if g.get("id") != "ui_smoke"]
    cfg["gates"] = {"preflight": pre, "session_done": gates.get("session_done") or []}
    cfg["bead_on_close"] = False
    return cfg


def test_checkout_run_branch_ok(monkeypatch):
    monkeypatch.setattr(
        fm,
        "_git_run",
        lambda *a, **k: type("P", (), {"returncode": 0, "stdout": "Switched", "stderr": ""})(),
    )
    out = fm.checkout_run_branch(session_id="test-session")
    assert out["ok"] is True
    assert out["branch"].startswith("mag/run-test-session-")


def test_checkout_run_branch_fallback_track(monkeypatch):
    monkeypatch.setattr(
        fm,
        "_git_run",
        lambda *a, **k: type("P", (), {"returncode": 1, "stdout": "", "stderr": "fail"})(),
    )
    monkeypatch.setattr(
        "mag.env_registry.activate_track",
        lambda t: {"ok": True, "track": t},
    )
    out = fm.checkout_run_branch(session_id="sess", track="operational")
    assert out["ok"] is False
    assert out["mode"] == "track_fallback"
    assert out["track"]["ok"] is True


def test_write_retrospective_sections(tmp_path, monkeypatch):
    retro_dir = tmp_path / "memory" / "runs" / "retrospectives"
    monkeypatch.setattr(fm, "RETRO_DIR", retro_dir)
    monkeypatch.setattr(fm, "_orchestrator_summary", lambda: {"next_action": "wake local"})

    sprint = {
        "phase": "closed",
        "ticks": 3,
        "report_path": "memory/runs/coding_session_run/x.json",
        "report": {
            "phase": "closed",
            "ticks": 3,
            "session_done_gates": [{"id": "build", "pass": True}],
            "git_diff_stat_head": " 2 files changed, 10 insertions(+)",
        },
    }
    path = fm.write_retrospective(
        session_id="test-retro",
        sprint=sprint,
        note="ship gate",
        branch={"ok": True, "branch": "mag/run-test"},
        behavioral={"ok": True},
    )
    assert path.endswith(".md")
    text = (retro_dir / "test-retro.md").read_text(encoding="utf-8")
    assert "## What went right" in text
    assert "## What went wrong" in text
    assert "## Next" in text
    assert "closed" in text
    assert "ship gate" in text


def test_factory_machine_preflight_fail(monkeypatch, tmp_path):
    report_dir = tmp_path / "memory" / "runs" / "factory_machine"
    retro_dir = tmp_path / "memory" / "runs" / "retrospectives"
    monkeypatch.setattr(fm, "REPORT_DIR", report_dir)
    monkeypatch.setattr(fm, "RETRO_DIR", retro_dir)
    monkeypatch.setattr(
        fm,
        "checkout_run_branch",
        lambda **_: {"ok": True, "branch": "mag/run-mock", "mode": "branch"},
    )
    monkeypatch.setattr(
        fm,
        "run_until_done",
        lambda **_: {
            "ok": False,
            "phase": "preflight_fail",
            "ticks": 0,
            "report_path": "memory/runs/coding_session_run/pf.json",
            "report": {"phase": "preflight_fail", "preflight": {"ok": False}},
        },
    )
    monkeypatch.setattr(fm, "behavioral_catalog", lambda **_: {"ok": True, "dry": False})

    cfg = _cfg()
    cfg["session_id"] = "fm-pf-fail"
    monkeypatch.setattr(fm, "load_config", lambda p=None: cfg)

    out = fm.factory_machine_run(config_path=CONFIG_PATH, note="x", dry=True)
    assert out.get("phase") == "preflight_fail"
    assert out.get("retrospective_path")
    assert report_dir.is_dir()
    reports = list(report_dir.glob("*.json"))
    assert len(reports) == 1
    saved = json.loads(reports[0].read_text(encoding="utf-8"))
    assert saved.get("schema") == fm.SCHEMA
    assert "branch" in saved.get("phases", {})


def test_factory_machine_status_empty(tmp_path, monkeypatch):
    report_dir = tmp_path / "memory" / "runs" / "factory_machine"
    retro_dir = tmp_path / "memory" / "runs" / "retrospectives"
    monkeypatch.setattr(fm, "REPORT_DIR", report_dir)
    monkeypatch.setattr(fm, "RETRO_DIR", retro_dir)
    monkeypatch.setattr(fm, "_git_out", lambda *a: "main" if a[0] == "rev-parse" else "")

    cfg = _cfg()
    monkeypatch.setattr(fm, "load_config", lambda p=None: cfg)
    st = fm.factory_machine_status()
    assert st.get("ok") is True
    assert st.get("branch") == "main"
