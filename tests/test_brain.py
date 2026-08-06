"""Brain API — multi-agent OS surface."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.brain import brain_act, brain_pulse


def test_brain_pulse_shape():
    p = brain_pulse()
    assert p["ok"] is True
    assert p["schema"] == "mag_brain.v1"
    assert "breadcrumbs" in p
    assert "endpoints" in p


def test_brain_unknown_action():
    out = brain_act({"action": "nope"})
    assert out["ok"] is False
    assert "actions" in out


def test_h_brain_get():
    from dashboard.rest import h_brain

    code, body = h_brain({}, None)
    assert code == 200
    assert body["schema"] == "mag_brain.v1"
