"""Growth cycle tests — self-contained with tmp_path monkeypatch."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import config
import mag.behavioral_synth as bsynth
import mag.growth_cycle as gc
import mag.improve as imp
import mag.training_events as te


@pytest.fixture
def growth_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Minimal disk layout for a dry growth cycle."""
    growth_dir = tmp_path / "memory" / "improve" / "growth"
    growth_dir.mkdir(parents=True)
    daily = tmp_path / "memory" / "improve" / "daily"
    daily.mkdir(parents=True)
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    (logs / "behavioral_events.jsonl").write_text(
        json.dumps({"kind": "collapse", "tool": "grep", "detail": "loop"}) + "\n",
        encoding="utf-8",
    )
    training = tmp_path / "memory" / "training"
    training.mkdir(parents=True)

    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(gc, "ROOT", tmp_path)
    monkeypatch.setattr(gc, "GROWTH_DIR", growth_dir)
    monkeypatch.setattr(gc, "STEER_PATH", growth_dir / "steer.yaml")
    monkeypatch.setattr(gc, "TRAIL", growth_dir / "growth_trail.jsonl")
    monkeypatch.setattr(gc, "REGISTRY", tmp_path / "memory" / "improve" / "model_registry.jsonl")
    monkeypatch.setattr(bsynth, "ROOT", tmp_path)
    monkeypatch.setattr(imp, "ROOT", tmp_path)
    monkeypatch.setattr(te, "ROOT", tmp_path)
    monkeypatch.setattr(te, "EVENTS_PATH", training / "events.jsonl")

    def _fake_probe(**_kw):
        return {
            "ok": True,
            "L0": {"ok": True, "lane": "L0"},
            "L1": {"ok": True, "lane": "L1", "model": "openrouter/auto"},
            "L2": {"ok": True, "lane": "L2"},
            "verdict": "L0 working",
        }

    def _fake_improve_cycle(**_kw):
        return {"ok": True, "fill": {"improve": 1, "handoff": 0}}

    monkeypatch.setattr(
        "models.probe.probe_all",
        _fake_probe,
    )
    monkeypatch.setattr(
        "mag.improve_loop.run_improve_cycle",
        _fake_improve_cycle,
    )
    monkeypatch.setattr(
        "mag.improve.scout",
        lambda **kw: {"ok": True, "candidates_added": 2, "mode": "scout"},
    )

    return tmp_path


def test_growth_cycle_writes_report_and_trail(growth_fixture):
    res = gc.run_growth_cycle(dry=False, drain_one=False)
    assert res.get("ok") is True
    report_path = growth_fixture / "memory" / "improve" / "growth"
    mds = list(report_path.glob("*-growth.md"))
    assert mds, "growth markdown not written"
    body = mds[0].read_text(encoding="utf-8")
    assert "# Growth cycle" in body
    assert "## Behavioral" in body
    assert "## Verdict" in body

    trail = report_path / "growth_trail.jsonl"
    assert trail.is_file()
    rows = [json.loads(ln) for ln in trail.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert rows[-1]["event"] == "cycle"


def test_growth_cycle_emits_three_body_episode(growth_fixture):
    gc.run_growth_cycle(dry=False, drain_one=False)
    events_path = growth_fixture / "memory" / "training" / "events.jsonl"
    assert events_path.is_file()
    rows = [json.loads(ln) for ln in events_path.read_text(encoding="utf-8").splitlines()]
    episodes = [r for r in rows if r.get("pattern") == "three_body_episode"]
    assert episodes
    ep = episodes[-1]
    assert "model" in ep.get("join", {})
    assert "harness" in ep.get("join", {})
    assert "behavioral" in ep.get("join", {})


def test_growth_cycle_steer_pause_skips_scout_and_drain(growth_fixture, monkeypatch):
    steer_path = growth_fixture / "memory" / "improve" / "growth" / "steer.yaml"
    steer_path.write_text("pause: true\nmax_improve: 1\n", encoding="utf-8")

    scout_called = {"n": 0}

    def _scout(**_kw):
        scout_called["n"] += 1
        return {"ok": True, "candidates_added": 99}

    drain_kwargs: dict = {}

    def _cycle(**kw):
        drain_kwargs.update(kw)
        return {"ok": True, "fill": {"improve": 0, "handoff": 0}}

    monkeypatch.setattr("mag.improve.scout", _scout)
    monkeypatch.setattr("mag.improve_loop.run_improve_cycle", _cycle)

    res = gc.run_growth_cycle(dry=False)
    assert scout_called["n"] == 0
    assert res["steps"]["scout"].get("mode") == "mining_summary"
    assert drain_kwargs.get("drain_one") is False

    body = (growth_fixture / "memory" / "improve" / "growth").glob("*-growth.md")
    md = next(body).read_text(encoding="utf-8")
    assert "mining:" in md or "scout paused" in md.lower() or "mining" in md.lower()


def test_growth_cycle_appends_model_registry(growth_fixture):
    gc.run_growth_cycle(dry=False, drain_one=False)
    reg = growth_fixture / "memory" / "improve" / "model_registry.jsonl"
    assert reg.is_file()
    row = json.loads(reg.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert "L0_ok" in row
    assert row["L1_model"] == "openrouter/auto"
