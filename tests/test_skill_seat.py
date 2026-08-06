"""Ponytail / caveman skill seats."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_pick_skill_code():
    from mag.skill_seat import pick_skill_for_goal

    assert pick_skill_for_goal("implement pytest fix mag/router.py") == "ponytail"
    assert pick_skill_for_goal("[priority] plan only BUILD spec acceptance") == "caveman"


def test_weaves_on_disk():
    from mag.skill_seat import load_skill

    assert "YAGNI" in load_skill("ponytail")
    assert "terse" in load_skill("caveman").lower()


def test_ponytail_gate():
    from mag.skill_seat import run_gate

    res = run_gate("ponytail")
    assert res.get("skill") == "ponytail"
    assert "pass" in res


def test_skill_gate_emits_training_event(tmp_path, monkeypatch):
    import mag.training_events as te
    from mag.skill_seat import run_gate

    events = tmp_path / "memory" / "training" / "events.jsonl"
    events.parent.mkdir(parents=True)
    monkeypatch.setattr(te, "EVENTS_PATH", events)

    def fake_audit(**_kw):
        return {"lean": True, "findings": []}

    import mag.ponytail_audit as pa

    monkeypatch.setattr(pa, "run_audit", fake_audit)
    run_gate("ponytail")
    lines = [ln for ln in events.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = __import__("json").loads(lines[0])
    assert row.get("pattern") == "skill_gate"
    assert "ponytail_pass" in (row.get("pattern_tags") or [])


def test_caveman_audit_runs():
    from mag.caveman_audit import run_audit

    res = run_audit(paths=["docs/ref/PONYTAIL_CAVEMAN_AUDIT.md"])
    assert res.get("schema") == "caveman_audit.v1"


def test_conductor_skill_overlay():
    from mag.conductor import conduct

    res = conduct("[build] implement frozen spec on branch", dry=True, mesh=False)
    assert res.get("overlay", {}).get("skill_seat") in ("ponytail", "caveman", None)
