"""Tests for ollama policy, desk model probe, gstd probe."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import desk_model_probe as dmp
from mag import gstd_probe as gp
from mag import ollama_policy as op


def test_enforce_one_hot(monkeypatch):
    monkeypatch.setenv("MAG_OLLAMA_ONE_HOT", "1")
    seen: list[str] = []

    monkeypatch.setattr(op, "list_loaded", lambda: [{"name": "gemma4:latest"}, {"name": "gemma4-desk:latest"}])
    monkeypatch.setattr(op, "_ollama_stop", lambda m: seen.append(m) or {"ok": True, "model": m})

    out = op.enforce_one_hot(keep="gemma4-desk", also_keep_janitor=True)
    assert out["ok"] is True
    assert "gemma4:latest" in seen


def test_enforce_one_hot_skipped(monkeypatch):
    monkeypatch.setenv("MAG_OLLAMA_ONE_HOT", "0")
    out = op.enforce_one_hot(keep="gemma4-desk")
    assert out.get("skipped") is True


def test_gstd_clone_inventory(tmp_path, monkeypatch):
    root = tmp_path / "gstdcoin"
    (root / "ai").mkdir(parents=True)
    (root / "A2A").mkdir()
    monkeypatch.setattr(gp, "CLONE_ROOTS", (root,))
    inv = gp._clone_inventory()
    assert inv["n"] == 2
    assert inv["ok"] is False


def test_gstd_route_recommendation_local_fast():
    route = gp._route_recommendation(
        local={"ok": True, "tokens_per_sec": 12, "gpu_pct": 100},
        gstd={"ok": True},
        clones={"n": 6},
    )
    assert route["primary"] == "local"


def test_desk_probe_emits_event(tmp_path, monkeypatch):
    report = tmp_path / "desk_model_probe.json"
    events: list[dict] = []
    monkeypatch.setattr(dmp, "REPORT_PATH", report)
    monkeypatch.setattr(dmp, "_tags", lambda: ["gemma4-desk:latest", "qwen-desk:latest"])
    monkeypatch.setattr(
        dmp,
        "_bench_model",
        lambda model, timeout=120: {
            "ok": True,
            "model": model,
            "tokens_per_sec": 15 if "qwen" in model else 10,
            "gpu_pct": 100,
            "elapsed_ms": 800,
        },
    )
    monkeypatch.setattr(
        "mag.training_events.emit",
        lambda *a, **kw: events.append({"pattern": a[0], **kw}) or {"event_id": "x"},
    )

    out = dmp.run_probe(pull_qwen=False)
    assert out["ok"] is True
    assert out["winner"] == "qwen-desk"
    assert report.is_file()
    assert events and events[0]["pattern"] == "route_decision"
