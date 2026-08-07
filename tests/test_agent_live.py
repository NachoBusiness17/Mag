"""Tests for agent live-turn status polling."""
from __future__ import annotations

import mag.agent_cli as ac


def test_get_live_turn_inactive():
    out = ac.get_live_turn("nonexistent-session")
    assert out["ok"] is True
    assert out["active"] is False
    assert out["session_id"] == "nonexistent-session"


def test_emit_status_updates_live_and_callback():
    seen: list[dict] = []

    def on_status(payload: dict) -> None:
        seen.append(payload)

    ac._clear_live_turn("test-live")
    ac._emit_status(
        on_status,
        "test-live",
        phase="model",
        detail="calling provider",
        round=1,
    )
    live = ac.get_live_turn("test-live")
    assert live["active"] is True
    assert live["phase"] == "model"
    assert live["detail"] == "calling provider"
    assert seen and seen[0]["phase"] == "model"
    ac._clear_live_turn("test-live")
    assert ac.get_live_turn("test-live")["active"] is False
