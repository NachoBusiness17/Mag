"""Tapestry visual grammar tests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_steiniger_temperature_range():
    from mag.tapestry_visual import steiniger_temperature

    assert 0.0 <= steiniger_temperature(tension_index=0.0) <= 1.0
    assert steiniger_temperature(tension_index=1.0) > steiniger_temperature(tension_index=0.0)


def test_knot_params_deterministic():
    from mag.tapestry_visual import knot_params_from_hash

    a = knot_params_from_hash("leaf-abc")
    b = knot_params_from_hash("leaf-abc")
    c = knot_params_from_hash("leaf-xyz")
    assert a == b
    assert a != c
    assert a[0] != a[1]


def test_visual_profile_shapes():
    from mag.tapestry_visual import visual_profile

    assert visual_profile("lattice", seed="x")["shape"] == "torus_knot"
    assert visual_profile("session", tension_index=0.8)["shape"] == "ellipsoid"
    assert visual_profile("run")["shape"] == "octahedron"


def test_build_tapestry_pack_has_visual():
    from mag.tapestry import build_tapestry_pack

    pack = build_tapestry_pack()
    assert pack.get("schema") == "mag_tapestry_pack.v3"
    nodes = pack.get("connections", {}).get("nodes") or []
    with_visual = [n for n in nodes if n.get("visual")]
    assert len(with_visual) >= 1
    sessions = [n for n in nodes if n.get("kind") == "session"]
    if sessions:
        assert sessions[0].get("visual", {}).get("shape") == "ellipsoid"
