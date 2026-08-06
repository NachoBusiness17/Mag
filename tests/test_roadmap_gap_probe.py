"""Roadmap gap probe smoke."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_roadmap_gap_probe_runs():
    import scripts.roadmap_gap_probe as rgp

    items = [rgp.score_item(it) for it in rgp.ROADMAP_ITEMS]
    assert len(items) >= 5
    assert all("gates" in i and "color" in i for i in items)
    desk = next(i for i in items if i["id"] == "desk")
    assert desk["gates"]["observe"] is True


def test_autorun_trust_gate_blocks_fill(monkeypatch):
    from mag.governor_autorun import fill_queue

    monkeypatch.setattr(
        "mag.desk_dialogue.read_trust_status",
        lambda: {"tier": 0, "slow_to_fast": "fail"},
    )
    out = fill_queue(max_improve=0, max_state=0, max_handoff=0, max_verkle=0)
    assert out.get("trust_blocked") is True
    assert "slow→fast" in str(out.get("trust_reason") or "")


def test_stack_includes_research():
    from mag.stack import build_stack_payload

    p = build_stack_payload(feed_limit=3, agent_limit=3)
    assert isinstance(p.get("research"), list)
    assert len(p["research"]) >= 3
    ids = {r["id"] for r in p["research"]}
    assert "spider" in ids
    assert "desk_health" in ids
