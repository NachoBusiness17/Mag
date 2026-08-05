"""Tests for Mag Autorun v1 integration."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import preferences as prefs
from mag import governor_autorun as ga


@pytest.fixture(autouse=True)
def _isolate_prefs(tmp_path, monkeypatch):
    pref_path = tmp_path / "mag_preferences.json"
    monkeypatch.setattr(prefs, "PREF_PATH", pref_path)
    monkeypatch.delenv("MAG_OPERATOR_ACTIVE", raising=False)
    monkeypatch.delenv("MAG_DRAINER", raising=False)
    monkeypatch.delenv("MAG_DRAINER_FORCE", raising=False)
    yield


def test_operator_active_pauses_autorun(monkeypatch):
    prefs.set_drainer(True)
    prefs.set_operator_active(True)
    from mag.autorun_common import autorun_pause_reason

    assert autorun_pause_reason() is not None

    res = ga.autorun_once(fill=False, dry=False)
    assert res.get("action") == "paused"


def test_autorun_allowed_when_drainer_on_operator_off():
    prefs.set_drainer(True)
    prefs.set_operator_active(False)
    assert prefs.autorun_allowed() is True


def test_route_task_uses_unified_router(monkeypatch):
    monkeypatch.setattr(
        "mag.router.route",
        lambda goal, depth=None, **kw: {
            "ok": True,
            "depth": "heavy_code",
            "provider": "deepseek",
            "mode": "queue",
            "launch": True,
            "executable": True,
            "job": "hard_code",
            "skills": ["patch-verify"],
        },
    )
    r = ga.route_task("implement failure kb module")
    assert r["provider"] == "deepseek"
    assert r["depth"] == "heavy_code"
    assert r["schema"] == "route.v2"


def test_enqueue_routed_blocks_plan_depth(monkeypatch, tmp_path):
    monkeypatch.setattr(ga, "route_task", lambda goal, depth=None: {
        "ok": True,
        "depth": "plan",
        "provider": "grok_tui",
        "executable": False,
        "hint": "pack only",
    })
    rec = ga.enqueue_routed("design system architecture")
    assert rec.get("ok") is False
    assert rec.get("error") == "plan_depth_not_queued"


def test_fkb_score_adjustment_penalizes_recurring(tmp_path, monkeypatch):
    from mag import failure_kb as fkb

    log_path = tmp_path / "failure_kb.jsonl"
    index_path = tmp_path / "signatures.json"
    monkeypatch.setattr(fkb, "LOG_PATH", log_path)
    monkeypatch.setattr(fkb, "INDEX_PATH", index_path)
    monkeypatch.setattr(fkb, "REMEDY_DIR", tmp_path / "remedies")

    for _ in range(4):
        fkb.log_failure(kind="tool_fail", tool="write_file", detail="bad shape", error="preflight")

    from mag.autorun_common import fkb_score_adjustment

    assert fkb_score_adjustment("preflight") < 0
