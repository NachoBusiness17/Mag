"""Mag power switch — kill / start / status."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_stack_status_schema():
    from mag.power import stack_status

    s = stack_status()
    assert s.get("schema") == "mag_power.v1"
    assert "headline" in s
    assert "services" in s
    assert "power_off" in s


def test_power_off_flag():
    from mag.power import clear_off, is_off, set_off

    clear_off()
    assert is_off() is False
    set_off()
    assert is_off() is True
    clear_off()
    assert is_off() is False


def test_timeout_improve_unchanged():
    from mag.orchestrator import IMPROVE_TIMEOUT, timeout_for_goal

    assert timeout_for_goal("[improve] x", tag="improve-a") == IMPROVE_TIMEOUT
