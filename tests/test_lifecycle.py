"""Passive lifecycle — on/off policy for stack pieces."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_build_lifecycle_schema():
    from mag.lifecycle import build_lifecycle

    lc = build_lifecycle()
    assert lc.get("schema") == "mag_lifecycle.v1"
    assert lc.get("ok") is True
    assert "pieces" in lc
    assert "posture" in lc
    ids = {p["id"] for p in lc["pieces"]}
    for need in ("backend", "dashboard", "lab", "drainer", "remote_seats", "browser_env"):
        assert need in ids
    for p in lc["pieces"]:
        assert p["should"] in ("on", "off")
        assert p["actual"] in ("on", "off")
        assert "token_class" in p
        assert "mode" in p


def test_remote_seats_passive_by_default():
    from mag.lifecycle import PIECE_DEFS, _policy_should

    remote = next(p for p in PIECE_DEFS if p["id"] == "remote_seats")
    should, reason = _policy_should(
        remote,
        power_off=False,
        wanted={},
        queue_depth=0,
        fleet_running=0,
        operator_active=False,
        drainer_allowed=False,
        browser_enabled=False,
    )
    assert should is False
    assert "idle" in reason.lower() or "never" in reason.lower() or "Passive" in reason or "off" in reason.lower()


def test_drainer_off_when_queue_empty():
    from mag.lifecycle import PIECE_DEFS, _policy_should

    drain = next(p for p in PIECE_DEFS if p["id"] == "drainer")
    should, _ = _policy_should(
        drain,
        power_off=False,
        wanted={"drainer": True},
        queue_depth=0,
        fleet_running=0,
        operator_active=False,
        drainer_allowed=True,
        browser_enabled=False,
    )
    assert should is False  # passive — no work to drain


def test_drainer_on_when_queue_and_allowed():
    from mag.lifecycle import PIECE_DEFS, _policy_should

    drain = next(p for p in PIECE_DEFS if p["id"] == "drainer")
    should, _ = _policy_should(
        drain,
        power_off=False,
        wanted={"drainer": True},
        queue_depth=2,
        fleet_running=0,
        operator_active=False,
        drainer_allowed=True,
        browser_enabled=False,
    )
    assert should is True


def test_power_off_forces_all_should_off():
    from mag.lifecycle import PIECE_DEFS, _policy_should

    for defn in PIECE_DEFS:
        should, reason = _policy_should(
            defn,
            power_off=True,
            wanted={"backend": True, "drainer": True},
            queue_depth=5,
            fleet_running=3,
            operator_active=False,
            drainer_allowed=True,
            browser_enabled=True,
        )
        assert should is False, defn["id"]
        assert "power off" in reason.lower()


def test_reconcile_dry_run():
    from mag.lifecycle import reconcile

    r = reconcile(dry_run=True)
    assert r.get("schema") == "mag_lifecycle_reconcile.v1"
    assert r.get("dry_run") is True
    assert "applied" in r
    assert "lifecycle" in r


def test_auto_reconcile_noop_or_dict(monkeypatch):
    from mag import lifecycle

    # force path always returns a dict
    r = lifecycle.auto_reconcile(force=True)
    assert r is not None
    assert r.get("ok") is True
    # disable via env
    monkeypatch.setenv("MAG_NO_AUTO_PASSIVE", "1")
    assert lifecycle.auto_reconcile() is None
    monkeypatch.delenv("MAG_NO_AUTO_PASSIVE", raising=False)
