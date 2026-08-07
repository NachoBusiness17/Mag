"""v3 research modules — loops, resonance, spider, conductor, grove."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_loops_registry():
    from mag.loops_registry import build_registry

    reg = build_registry()
    assert reg.get("schema") == "mag_loops_registry.v1"
    assert reg["summary"]["total"] >= 5
    ids = {r["id"] for r in reg["loops"]}
    assert "resonance" in ids and "spider" in ids
    assert "switchboard" in ids


def test_resonance_top_cards():
    from mag.resonance import score_echoes, tick

    cards = score_echoes("autorun improve mag", limit=3)
    assert isinstance(cards, list)
    res = tick("test goal", dry=True)
    assert res.get("ok") is True
    assert res.get("written") is False


def test_resonance_l0e_format():
    from mag.resonance import format_l0e

    text = format_l0e([{"kind": "remedy", "title": "test", "excerpt": "x", "path": "a/b", "score": 1.0}])
    assert "L0e Resonance" in text


def test_spider_tick_dry():
    from mag.spider import tick

    res = tick(dry=True, inject=False)
    assert res.get("ok") is True
    assert "signals" in res


def test_conductor_phase_detect():
    from mag.conductor import conduct, detect_phase

    assert detect_phase("[priority] plan only architecture") == "plan"
    assert detect_phase("[build] implement pytest") == "build"
    assert detect_phase("audit only ponytail diff") == "audit"
    res = conduct("mag autorun smoke test", dry=True)
    assert res.get("schema") == "conductor.v1"
    assert res.get("route")


def test_grove_build_dry():
    from mag.grove import build

    res = build(dry=True)
    assert res.get("ok") is True
    assert res.get("dry") is True


def test_context_pack_has_resonance_layer(monkeypatch):
    from mag.context_pack import build_context_pack

    pack = build_context_pack()
    layers = pack.get("layers") or []
    assert "L0e_resonance" in layers
    assert "resonance_cards" in pack
