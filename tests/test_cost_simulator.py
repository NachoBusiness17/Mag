"""Cost simulator smoke."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_estimate_wave():
    from mag.cost_simulator import estimate_wave

    w = estimate_wave("pytest-epic", improve_n=1, build_waves=1, audits=0, plan=False)
    assert w.get("ok") is True
    assert w.get("summary", {}).get("usd_est") is not None


def test_estimate_goal():
    from mag.cost_simulator import estimate_goal

    g = estimate_goal("[improve] fix smoke test", dry=True)
    assert g.get("ok") is True
    assert g.get("total_usd_est") is not None
