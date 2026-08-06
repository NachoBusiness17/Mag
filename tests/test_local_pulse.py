"""Local model pulse — CPU + desk session thinking signal."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import local_pulse as lp


def test_build_local_pulse_idle(monkeypatch):
    monkeypatch.setattr(lp, "_ollama_ps", lambda timeout=0.6: {"ok": True, "models": [], "n": 0})
    monkeypatch.setattr(
        lp,
        "_cpu_samples",
        lambda: {"system_pct": 12.0, "ollama_proc_pct": 0.0, "procs": []},
    )
    monkeypatch.setattr(lp, "_read_desk_flag", lambda: {})

    out = lp.build_local_pulse(proc_threshold=25, sys_threshold=55)
    assert out["schema"] == "mag_local_pulse.v1"
    assert out["state"] == "idle"
    assert out["thinking"] is False


def test_build_local_pulse_thinking_from_cpu(monkeypatch):
    monkeypatch.setattr(
        lp,
        "_ollama_ps",
        lambda timeout=0.6: {"ok": True, "models": [{"name": "gemma4"}], "n": 1},
    )
    monkeypatch.setattr(
        lp,
        "_cpu_samples",
        lambda: {"system_pct": 72.0, "ollama_proc_pct": 8.0, "procs": ["ollama.exe"]},
    )
    monkeypatch.setattr(lp, "_read_desk_flag", lambda: {})

    out = lp.build_local_pulse(proc_threshold=25, sys_threshold=55)
    assert out["thinking"] is True
    assert out["state"] == "thinking"
    assert "system_cpu" in out["sources"]


def test_build_local_pulse_desk_session(monkeypatch):
    monkeypatch.setattr(lp, "_ollama_ps", lambda timeout=0.6: {"ok": True, "models": [], "n": 0})
    monkeypatch.setattr(
        lp,
        "_cpu_samples",
        lambda: {"system_pct": 5.0, "ollama_proc_pct": 0.0, "procs": []},
    )
    monkeypatch.setattr(
        lp,
        "_read_desk_flag",
        lambda: {"active": True, "model": "gemma4", "source": "desk_dialogue", "ts": "2026-08-05"},
    )

    out = lp.build_local_pulse()
    assert out["thinking"] is True
    assert "desk_session" in out["sources"]


def test_set_local_thinking_flag(tmp_path, monkeypatch):
    flag = tmp_path / "local_thinking.json"
    monkeypatch.setattr(lp, "THINKING_FLAG", flag)

    lp.set_local_thinking(active=True, model="gemma4", source="test")
    assert flag.is_file()
    data = json.loads(flag.read_text(encoding="utf-8"))
    assert data["active"] is True
    assert data["model"] == "gemma4"

    lp.set_local_thinking(active=False)
    assert not flag.is_file()


def test_h_local_pulse_handler():
    from dashboard.rest import h_local_pulse

    code, body = h_local_pulse({}, None)
    assert code == 200
    assert body["ok"] is True
    assert body["schema"] == "mag_local_pulse.v1"
    assert "cpu" in body
    assert "state" in body
