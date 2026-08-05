"""Improve stack integration: REST, scout_due_today, autopilot scout."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mag.autopilot import autopilot_once


def test_scout_due_today_fresh_clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    imp_dir = tmp_path / "memory" / "improve"
    imp_dir.mkdir(parents=True)
    (imp_dir / "state.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    import mag.improve as imp

    monkeypatch.setattr(imp, "ROOT", tmp_path)
    assert imp.scout_due_today() is True


def test_scout_due_today_after_scout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    imp_dir = tmp_path / "memory" / "improve"
    imp_dir.mkdir(parents=True)
    from datetime import datetime, timezone

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (imp_dir / "state.json").write_text(json.dumps({"last_day": day}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    import mag.improve as imp

    monkeypatch.setattr(imp, "ROOT", tmp_path)
    assert imp.scout_due_today() is False


def test_improve_light_status_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    imp_dir = tmp_path / "memory" / "improve"
    imp_dir.mkdir(parents=True)
    (imp_dir / "state.json").write_text("{}", encoding="utf-8")
    (imp_dir / "candidates.jsonl").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    import mag.improve as imp

    monkeypatch.setattr(imp, "ROOT", tmp_path)
    st = imp.improve_light_status()
    assert "scout_due_today" in st
    assert "total_candidates" in st
    assert st["total_candidates"] == 0


def test_improve_get_handler():
    from dashboard.rest import h_improve_status

    code, body = h_improve_status({}, None)
    assert code == 200
    assert body.get("ok") is True
    assert "scout_due_today" in body


def test_improve_post_toggle():
    from dashboard.rest import h_improve_post

    code, body = h_improve_post({}, {"enabled": True})
    assert code == 200
    assert body.get("ok") is True
    assert body.get("improve", {}).get("enabled") is True


def test_improve_post_status_mode():
    from dashboard.rest import h_improve_post

    code, body = h_improve_post({}, {"mode": "status"})
    assert code == 200
    assert body.get("ok") is True
    assert "total_candidates" in body


def test_autopilot_skips_scout_when_already_ran(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    imp_dir = tmp_path / "memory" / "improve"
    imp_dir.mkdir(parents=True)
    from datetime import datetime, timezone

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (imp_dir / "state.json").write_text(json.dumps({"last_day": day}), encoding="utf-8")
    (imp_dir / "candidates.jsonl").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    import mag.improve as imp

    monkeypatch.setattr(imp, "ROOT", tmp_path)
    res = autopilot_once(scout=None, queue_improve=False, governor=False, drain=False)
    assert res.get("ok") is True
    assert "improve" not in res
    steps = " ".join(str(s) for s in (res.get("steps") or []))
    assert "skipped" in steps or "already ran" in steps
