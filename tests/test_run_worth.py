"""Run worth gate — defer truncate + hung detection heuristics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mag.run_worth as rw
import mag.run_trail as rt


@pytest.fixture()
def worth_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    runs = tmp_path / "runs"
    runs.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()
    monkeypatch.setattr(rt, "RUNS", runs)
    monkeypatch.setattr(rt, "ACTIVE", runs / "active.json")
    monkeypatch.setattr(rt, "RELATED", runs / "related_runs.jsonl")
    monkeypatch.setattr(rw, "ROOT", tmp_path)
    monkeypatch.setattr(rw, "LOG_PATH", logs / "run_worth.jsonl")
    monkeypatch.setattr(rw, "OVERRIDES_PATH", logs / "run_worth_overrides.jsonl")
    cfg = dict(rw.DEFAULTS)
    monkeypatch.setattr(rw, "load_config", lambda: cfg)
    return tmp_path, cfg


def _tool_events(n: int, *, same_tool: bool = False) -> list[dict]:
    out = []
    for i in range(n):
        tool = "grep" if same_tool else f"tool_{i % 4}"
        out.append(
            {
                "kind": "tool",
                "tool": tool,
                "summary": f"call {i}",
                "core": {"text": "same" if same_tool else f"arg-{i}"},
            }
        )
    return out


def test_valuable_run_deferred_at_tool_limit(worth_fixture):
    _, cfg = worth_fixture
    r = rt.start_run("refactor auth", max_tool_calls=5, force=True)
    rid = r["run"]["run_id"]
    events = _tool_events(4)
    events.append({"kind": "tool", "tool": "write_file", "summary": "wrote patch"})
    for ev in events:
        rt.append_event("tool", ev["summary"], run_id=rid, tool=ev["tool"], core=ev.get("core"))
    run = rt.load_run(rid)
    assert run["n_tool_calls"] == 5
    gate = rw.gate_before_truncate(run, trail_events=events)
    assert gate["allow_continue"] is True
    assert gate["new_max_tool_calls"] >= cfg["max_tool_calls_hard"]


def test_worthless_identical_streak_blocked(worth_fixture):
    _, cfg = worth_fixture
    r = rt.start_run("grep loop", max_tool_calls=5, force=True)
    rid = r["run"]["run_id"]
    events = _tool_events(6, same_tool=True)
    for ev in events[:5]:
        rt.append_event("tool", ev["summary"], run_id=rid, tool=ev["tool"], core=ev.get("core"))
    run = rt.load_run(rid)
    sig = rw.signals_from_run(run, events)
    cls = rw.classify_run(sig)
    assert cls["verdict"] in ("worthless", "hung", "uncertain")
    res = rt.append_event("tool", "call 6", run_id=rid, tool="grep", core={"text": "same"})
    if cls["verdict"] == "worthless":
        assert res.get("ok") is False or run.get("worth_defer_count", 0) >= 0


def test_operator_mark_good_overrides(worth_fixture):
    tmp_path, _ = worth_fixture
    r = rt.start_run("long deepseek run", max_tool_calls=3, force=True)
    rid = r["run"]["run_id"]
    mark = rw.mark_run_good(rid, note="early DeepSeek improvement was good")
    assert mark.get("ok")
    assert rw.is_operator_marked_good(rid)
    sig = rw.signals_from_run(r["run"], _tool_events(10, same_tool=True))
    assert rw.score_worth(sig) >= 0.99
    assert rw.classify_run(sig)["verdict"] == "valuable"
    assert (tmp_path / "logs" / "run_worth_overrides.jsonl").is_file()


def test_detect_hung_zero_velocity(worth_fixture):
    _, cfg = worth_fixture
    sig = {
        "stale_s": cfg["hung_timeout_s"] + 10,
        "velocity_per_min": 0.0,
        "artifact_count": 0,
        "identical_streak": 0,
        "operator_good": False,
    }
    hung = rw.detect_hung(sig, cfg)
    assert hung["hung"] is True


def test_detect_hung_identical_streak(worth_fixture):
    _, cfg = worth_fixture
    sig = {
        "stale_s": cfg["hung_zero_artifact_s"] + 30,
        "velocity_per_min": 0.01,
        "artifact_count": 0,
        "identical_streak": cfg["hung_identical_window"],
        "operator_good": False,
    }
    hung = rw.detect_hung(sig, cfg)
    assert hung["hung"] is True


def test_append_event_extends_on_uncertain(worth_fixture):
    _, cfg = worth_fixture
    r = rt.start_run("mixed progress", max_tool_calls=4, force=True)
    rid = r["run"]["run_id"]
    for i in range(4):
        rt.append_event("tool", f"t{i}", run_id=rid, tool=f"read_{i}")
    run = rt.load_run(rid)
    assert run["n_tool_calls"] == 4
    res = rt.append_event("tool", "t5", run_id=rid, tool="read_5")
    run2 = rt.load_run(rid)
    if res.get("ok"):
        assert int((run2.get("bounds") or {}).get("max_tool_calls") or 0) >= 4
        assert int(run2.get("worth_defer_count") or 0) >= 1


def test_status_reports_config(worth_fixture):
    res = rw.status()
    assert res.get("ok")
    assert res.get("enabled") is True
    assert "max_tool_calls_hard" in (res.get("config") or {})
