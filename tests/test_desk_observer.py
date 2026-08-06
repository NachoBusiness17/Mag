"""Desk observer — steal protocol (rules only, no LLM)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import desk_observer as obs  # noqa: E402


def test_score_passes_clean_turn():
    ctx = {
        "echo": {"detected": False, "streak": 0},
        "pressure": {"intervene": False, "reasons": []},
        "artifact": "mag/build_audit.py",
        "desk_task": "Local: append Status with build_audit scaffold.",
        "recent_turns": [
            {
                "speaker": "local",
                "reply": "### Reply\nScaffold listed.\n\n### Canvas edit\n",
                "canvas_edit": "mag/build_audit.py and tests/test_build_audit.py",
                "wake_blocked": False,
            }
        ],
    }
    row = obs.score_turn_rules(ctx)
    assert row.get("pass") is True
    assert (row.get("score") or 0) >= 0.55


def test_score_fails_echo():
    ctx = {
        "echo": {"detected": True, "streak": 3},
        "pressure": {"intervene": True, "reasons": ["echo_without_commit"]},
        "artifact": "mag/build_audit.py",
        "desk_task": "scaffold",
        "recent_turns": [{"speaker": "local", "reply": "same", "canvas_edit": "", "wake_blocked": True}],
    }
    row = obs.score_turn_rules(ctx)
    assert row.get("pass") is False
    assert "echo_without_commit" in (row.get("reasons") or [])


def test_build_steer_mentions_artifact():
    ctx = {"artifact": "mag/build_audit.py", "desk_task": "Local: file list"}
    steer = obs.build_steer_packet(ctx, {"score": 0.3, "reasons": ["weak_sprint_alignment"]})
    assert "build_audit" in steer


def test_observer_tick_skipped_when_disabled(monkeypatch):
    from mag.coding_session_loop import load_config

    orig = load_config

    def _cfg():
        c = orig()
        c["steal_protocol"] = {"enabled": False}
        return c

    monkeypatch.setattr("mag.coding_session_loop.load_config", _cfg)
    out = obs.observer_tick(inject=False)
    assert out.get("skipped")


def test_verifier_blocks_without_artifact(monkeypatch):
    monkeypatch.setattr(
        "mag.desk_observer.collect_observer_context",
        lambda **_: {
            "echo": {"detected": False},
            "pressure": {},
            "artifact": "mag/build_audit.py",
            "desk_task": "scaffold",
            "recent_turns": [
                {"speaker": "local", "reply": "### Reply\nok", "canvas_edit": "mag/build_audit.py", "wake_blocked": False}
            ],
        },
    )
    monkeypatch.setattr(
        "mag.coding_session_orchestrator.assess_sprint_status",
        lambda **_: {
            "active_sprint": "sprint_1_skeleton",
            "sprint_checks": [{"sprint": "sprint_1_skeleton", "pass": False}],
        },
    )
    out = obs.verify_sprint_handoff(config={"ok": True, "steal_protocol": {"enabled": True, "verifier_before_advance": True}})
    assert out.get("approve_advance") is False
    assert "artifact_gate_open" in (out.get("blockers") or [])
