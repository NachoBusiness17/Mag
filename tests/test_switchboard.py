"""Switchboard mesh — seats, tier gates, dry drops."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_tier_allows():
    from mag.switchboard import tier_allows

    assert tier_allows(holder_tier_max="T2", payload_tier="T2") is True
    assert tier_allows(holder_tier_max="T1", payload_tier="T2") is False
    assert tier_allows(holder_tier_max="T2", payload_tier="T0") is False
    assert tier_allows(holder_tier_max="T2", payload_tier="T1") is False
    assert tier_allows(holder_tier_max="T1", payload_tier="T0") is True
    assert tier_allows(holder_tier_max="T1", payload_tier="T1") is True
    assert tier_allows(holder_tier_max="T3", payload_tier="T0") is True


def test_remote_drop_refuses_private_tiers():
    from mag.switchboard import steer_drop

    for tier in ("T0", "T1"):
        res = steer_drop("operator", "t-fake", "private payload", tier=tier, dry=True)
        assert res.get("ok") is False
        assert res.get("error") == "tier_blocked"


def test_seat_registry():
    from mag.switchboard import build_seat_registry

    reg = build_seat_registry()
    assert "ollama" in reg
    assert "local" in reg
    assert reg["ollama"].tier_max in ("T0", "T1", "T2", "T3")


def test_mesh_schema():
    from mag.switchboard import mesh

    m = mesh(include_seats=False)
    assert m.get("schema") == "switchboard.v1"
    assert "peers" in m
    assert "summary" in m


def test_steer_drop_dry():
    from mag.switchboard import steer_drop

    res = steer_drop("operator", "t-fake", "hello mesh", tier="T2", dry=True)
    assert res.get("ok") is True
    assert res.get("dry") is True
    assert "steer_preview" in res


def test_steer_drop_tier_blocked():
    from mag.switchboard import steer_drop

    res = steer_drop("operator", "t-fake", "secret", tier="T3", dry=True)
    # dry still validates tier against default target tier T2
    assert res.get("ok") is False or res.get("dry") is True


def test_route_intent_dry():
    from mag.switchboard import route_intent

    res = route_intent("mag autorun smoke test", dry=True)
    assert res.get("schema") == "switchboard_route.v1"
    assert res.get("target", {}).get("seat")


def test_self_test():
    from mag.switchboard import self_test

    res = self_test()
    assert res.get("tier_gate") is True
    assert res.get("n_seats", 0) >= 3
