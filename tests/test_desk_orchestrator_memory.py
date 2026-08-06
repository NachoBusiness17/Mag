"""Orchestrator memory packets for slow/fast seats."""
from __future__ import annotations

from mag.desk_orchestrator_memory import (
    build_local_memory_packet,
    compose_local_wake_payload,
)


def test_local_memory_minimal_mode():
    fid = {
        "last_peer_message": 'Post exactly one bare line: `4... exd4` — nothing else.',
        "recent_dialogue": [],
    }
    mem = build_local_memory_packet(fidelity=fid, operator_note="chess test")
    assert mem["bandwidth"] == "low"
    assert mem["required_canvas_line"] == "4... exd4"
    assert mem["mode"] in ("minimal", "recovery", "continue", "bootstrap")
    payload = compose_local_wake_payload(memory=mem)
    assert "Orchestrator memory" in payload
    assert "4... exd4" in payload
    assert "one bare line" in payload.lower() or "one line" in payload.lower()


def test_compose_local_recovery():
    mem = {
        "mode": "recovery",
        "memory_bullets": ["Recovery: no headers"],
        "required_canvas_line": "4... Nf6",
        "board_tail": "1. e4 e5 4. d4",
    }
    payload = compose_local_wake_payload(memory=mem, wake_note="try again")
    assert "4... Nf6" in payload
    assert "Recovery" in payload
