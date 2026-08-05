"""Improve loop — cloud handoff + cycle wiring."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_cloud_handoff_write():
    from mag.improve_loop import ingest_cloud_handoffs, write_cloud_handoff

    res = write_cloud_handoff(claim="smoke test claim", source="pytest")
    assert res.get("ok") is True
    assert res.get("path")
    rows = ingest_cloud_handoffs()
    assert any(r.get("run_id") == res.get("run_id") for r in rows)


def test_improve_cycle_schema():
    from mag.improve_loop import run_improve_cycle

    res = run_improve_cycle(source="pytest", max_improve=0, drain_one=False)
    assert res.get("schema") == "improve_loop.v1"
    assert "nervous" in res or "nervous_error" in res
