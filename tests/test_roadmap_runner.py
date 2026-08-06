from __future__ import annotations

import json


def test_selects_first_unpassed_planned_gate(monkeypatch):
    from mag import roadmap_runner as rr

    monkeypatch.setattr(rr, "_passed", lambda version: set())
    out = rr.select_next()
    assert out["ok"] is True
    assert out["version"] == "v5"
    assert out["gate"]["id"] == "gstd_t0_probe"


def test_select_skips_recorded_gate(monkeypatch):
    from mag import roadmap_runner as rr

    monkeypatch.setattr(rr, "_passed", lambda version: {"gstd_t0_probe"} if version == "v5" else set())
    out = rr.select_next()
    assert out["gate"]["id"] == "vast_train_dry"


def test_tbd_version_refuses_autonomous_run():
    from mag.roadmap_runner import select_next

    out = select_next(version="v6")
    assert out["ok"] is False
    assert out["error"] == "curriculum_tbd"


def test_compile_files_frozen_build_and_config(tmp_path, monkeypatch):
    from mag import roadmap_runner as rr

    monkeypatch.setattr(rr, "BUILD_DIR", tmp_path / "queue" / "handoff")
    monkeypatch.setattr(rr, "RUN_CONFIG_DIR", tmp_path / "memory" / "working")
    monkeypatch.setattr(rr, "EVIDENCE_DIR", tmp_path / "memory" / "runs")
    selection = {
        "ok": True,
        "version": "v5",
        "era": "forest_pipe",
        "meaning": "optional seats",
        "commitment": "mag-release-v5-001",
        "gate": {"id": "gstd_t0_probe"},
        "sources": [],
    }
    out = rr.compile_run(selection)
    assert out["ok"] is True
    build = (rr.BUILD_DIR / "BUILD-roadmap-v5-gstd-t0-probe.md").read_text(encoding="utf-8")
    assert "**Status:** frozen" in build
    assert "one gate-sized branch" in build
    cfg = rr.RUN_CONFIG_DIR / "v5-gstd-t0-probe.yaml"
    assert cfg.is_file()
    assert "roadmap-v5-gstd-t0-probe" in cfg.read_text(encoding="utf-8")


def test_prepare_does_not_start_factory(monkeypatch):
    from mag import roadmap_runner as rr

    monkeypatch.setattr(rr, "select_next", lambda **kw: {"ok": True, "version": "v5", "gate": {"id": "g"}, "sources": []})
    monkeypatch.setattr(rr, "compile_run", lambda selection: {"ok": True, "config_path": "x", "selection": selection})
    out = rr.run_next(prepare_only=True)
    assert out["ok"] is True


def test_run_delegates_compiled_contract_to_factory(monkeypatch):
    from mag import roadmap_runner as rr

    contract = {"ok": True, "config_path": "memory/working/test.yaml", "branch_prefix": "mag/roadmap-v5-gate", "goal": "goal"}
    seen = {}
    monkeypatch.setattr(rr, "select_next", lambda **kw: {"ok": True})
    monkeypatch.setattr(rr, "compile_run", lambda selection: contract)

    def fake_factory(**kwargs):
        seen.update(kwargs)
        return {"ok": True, "phase": "done"}

    monkeypatch.setattr("mag.factory_machine.factory_machine_run", fake_factory)
    out = rr.run_next(max_ticks=7)
    assert out["ok"] is True
    assert seen["branch_prefix"] == contract["branch_prefix"]
    assert seen["max_ticks"] == 7
    assert seen["force_new_seed"] is True
