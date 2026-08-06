"""Seat registry union — desktop/cloud seats visible to orchestrator + switchboard."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_register_external():
    from mag.seat_registry import register, unregister

    rec = register(seat="cursor", goal="test session", parent="pytest", mode="interactive")
    assert rec.get("ok") is True
    tid = rec["task_id"]
    assert tid.startswith("ext-")
    assert rec.get("mag_task_id") == tid
    done = unregister(tid, status="done")
    assert done.get("ok") is True


def test_timeout_for_improve():
    from mag.orchestrator import IMPROVE_TIMEOUT, DEFAULT_TIMEOUT, timeout_for_goal

    assert timeout_for_goal("[improve] fix flaky test", tag="improve-c1") == IMPROVE_TIMEOUT
    assert timeout_for_goal("normal job", tag="api") == DEFAULT_TIMEOUT
    assert IMPROVE_TIMEOUT < DEFAULT_TIMEOUT


def test_mesh_peers_includes_external():
    from mag.seat_registry import mesh_peers, register, unregister

    rec = register(seat="cloud", goal="cloud agent", parent="pytest", mode="cloud")
    tid = rec["task_id"]
    peers = mesh_peers()
    assert any(p.get("task_id") == tid for p in peers)
    unregister(tid)


def test_switchboard_sees_external():
    from mag.seat_registry import register, unregister
    from mag.switchboard import mesh

    rec = register(seat="cursor", goal="switchboard test", parent="pytest")
    tid = rec["task_id"]
    m = mesh(include_seats=False)
    peer_ids = [p.get("task_id") for p in m.get("peers") or []]
    assert tid in peer_ids
    unregister(tid)
