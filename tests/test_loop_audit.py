"""Tests for mag.loop_audit — trail mining + verkle goal normalization."""
from __future__ import annotations

import json

from mag.loop_audit import (
    analyze_autorun_trail,
    plan_fingerprint,
    run_audit,
    verkle_gap_goal,
)


def test_verkle_gap_goal_session_scoped():
    gap = {
        "detail": "residual without knot: mag-agent-cli.json",
        "action": "summarize-session for mag-agent-cli",
        "severity": "warn",
    }
    assert verkle_gap_goal(gap) == "[verkle] summarize-session mag-agent-cli"


def test_plan_fingerprint_stable():
    p1 = {
        "orchestrator_queued": [
            {"goal": "[test] smoke"},
            {"goal": "[verkle] residual without knot: x.json — run: summarize-session for x"},
        ]
    }
    p2 = {
        "orchestrator_queued": [
            {"goal": "[verkle] other detail — run: summarize-session for x"},
            {"goal": "[test] smoke"},
        ]
    }
    assert plan_fingerprint(p1) == plan_fingerprint(p2)


def test_analyze_autorun_detects_plan_theater():
    rows = []
    for _ in range(90):
        rows.append(
            {
                "schema": "autorun_once.v1",
                "action": "busy",
                "plan": {
                    "orchestrator_queued": [{"goal": "[test] stuck goal"}],
                },
            }
        )
    out = analyze_autorun_trail(rows)
    kinds = {f["kind"] for f in out["findings"]}
    assert "plan_theater" in kinds
    assert out["top_replan"][0]["count"] == 90


def test_run_audit_schema(tmp_path, monkeypatch):
    trail = tmp_path / "governor_autorun_trail.jsonl"
    trail.write_text(
        json.dumps({"schema": "autorun_once.v1", "action": "paused", "plan": {"orchestrator_queued": []}})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("mag.loop_audit.AUTORUN_TRAIL", trail)
    audit = run_audit(tail=10)
    assert audit.get("schema") == "loop_audit.v1"
    assert "recommendations" in audit
