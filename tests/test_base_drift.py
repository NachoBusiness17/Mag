"""Base graph freeze + drift FILE — Lessig architecture for stateless seats."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import run_trail as rt


@pytest.fixture()
def isolated_runs(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(rt, "RUNS", runs)
    monkeypatch.setattr(rt, "ACTIVE", runs / "active.json")
    monkeypatch.setattr(rt, "RELATED", runs / "related_runs.jsonl")
    # tip snapshot still reads real tip if present — ok; base_id still stable enough
    return runs


def test_start_run_freezes_base(isolated_runs):
    r = rt.start_run("base-freeze-test", seat="local", force=True, git_sha="deadbeefcafe")
    assert r.get("ok")
    base = r.get("base") or (r.get("run") or {}).get("base")
    assert base and base.get("base_id")
    assert len(base["base_id"]) == 16
    assert base.get("git_sha") == "deadbeefcafe"
    run = r["run"]
    assert run["base"]["base_id"] == base["base_id"]
    assert "base_drift" in (run.get("compose") or {}).get("steals", [])


def test_file_agent_core_stamps_base_and_locus(isolated_runs):
    r = rt.start_run("drift-stamp", seat="grok_tui", force=True, git_sha="abc123")
    rid = r["run"]["run_id"]
    base_id = r["base"]["base_id"]
    a = rt.file_agent_core(
        "security",
        "auth hole",
        run_id=rid,
        locus="src/auth.py",
        drift_kind="finding",
        evidence="src/auth.py:12",
        text="missing check",
    )
    assert a.get("ok"), a
    core = a["event"]["core"]
    assert core["base_id"] == base_id
    assert core["locus"] == "src/auth.py"
    assert core["drift_kind"] == "finding"
    assert core["schema"] == rt.SCHEMA_DRIFT


def test_base_id_mismatch_rejected(isolated_runs):
    r = rt.start_run("mismatch", seat="local", force=True)
    rid = r["run"]["run_id"]
    bad = rt.file_agent_core(
        "x",
        "y",
        run_id=rid,
        base_id="ffffffffffffffff",
    )
    assert not bad.get("ok")
    assert bad.get("error") == "base_id_mismatch"


def test_list_drifts_clusters(isolated_runs):
    r = rt.start_run("list-drifts", seat="local", force=True)
    rid = r["run"]["run_id"]
    rt.file_agent_core("a", "one", run_id=rid, locus="mod.a", drift_kind="add")
    rt.file_agent_core("b", "two", run_id=rid, locus="mod.a", drift_kind="finding")
    rt.file_agent_core("c", "three", run_id=rid, locus="mod.b", drift_kind="gap")
    d = rt.list_drifts(rid)
    assert d.get("ok")
    assert d["n"] == 3
    assert d["by_locus"].get("mod.a") == 2
    assert d["base_id"] == r["base"]["base_id"]


def test_append_agent_probe_injects_base(isolated_runs):
    r = rt.start_run("inject", seat="local", force=True)
    rid = r["run"]["run_id"]
    base_id = r["base"]["base_id"]
    # raw append with kind agent_probe and incomplete core — architecture stamps base
    a = rt.append_event(
        "agent_probe",
        "raw probe",
        run_id=rid,
        core={"label": "raw", "text": "hi"},
    )
    assert a.get("ok"), a
    assert a["event"]["core"]["base_id"] == base_id


def test_snapshot_base_stable_for_same_inputs(isolated_runs, monkeypatch):
    monkeypatch.setattr(rt, "_tip_root_short", lambda: ("tipabc", "leaf.json", 3))
    monkeypatch.setattr(rt, "_git_head", lambda cwd=None: "githash")
    b1 = rt.snapshot_base(git_sha="githash", pack_ts="fixed-ts")
    b2 = rt.snapshot_base(git_sha="githash", pack_ts="fixed-ts")
    assert b1["base_id"] == b2["base_id"]
