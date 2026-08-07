"""Temperature stacks — adjustable timings, pointers, gap track."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_registry_loads_stacks():
    from mag.temperature_stack import registry

    reg = registry()
    snap = reg.snapshot()
    assert snap["schema"] == "mag_temperature_stacks.v1"
    assert "cold" in reg.stacks
    assert "scarce" in reg.stacks
    assert reg.loop_s("supervisor_check_s", 5) >= 2


def test_resolve_improve_and_code():
    from mag.temperature_stack import stack_for_goal, timeout_for_goal

    imp = stack_for_goal("[improve] scout harness", tag="improve-a")
    assert imp.id == "improve"
    assert timeout_for_goal("[improve] x", tag="improve") == imp.timeout_s

    code = stack_for_goal("implement dual-progress fix")
    assert code.id in ("warm", "hot")  # implement → warm keywords


def test_timeout_orchestrator_uses_stacks():
    from mag.orchestrator import timeout_for_goal as orch_timeout
    from mag.temperature_stack import stack_for_goal

    t = orch_timeout("[improve] playbook")
    assert t == stack_for_goal("[improve] playbook").timeout_s
    assert orch_timeout("x", timeout=42) == 42


def test_size_boost_timeout():
    from mag.temperature_stack import TemperatureStack

    st = TemperatureStack(id="hot", timeout_s=100)
    assert st.timing.scaled_timeout(size_hint=0) == 100
    assert st.timing.scaled_timeout(size_hint=40000) > 100


def test_pointer_knot_files():
    from mag.temperature_stack import file_pointer_knot

    r = file_pointer_knot(
        "https://github.com/openclaw/openclaw",
        kind="github",
        summary="computer-use research",
        tags=["openclaw"],
    )
    assert r.get("ok") is True
    assert r["knot"]["kind"] == "github"
    assert r["knot"]["leaf_hash"]


def test_track_loop_gap_dedupe():
    from mag.temperature_stack import track_loop_gap

    a = track_loop_gap("test_gap_unique_xyz", detail="unit", where="tests", force=True)
    assert a.get("ok") is True
    b = track_loop_gap("test_gap_unique_xyz", detail="unit", where="tests", force=False)
    assert b.get("skipped") is True
