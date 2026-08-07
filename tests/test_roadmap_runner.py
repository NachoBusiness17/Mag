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


def test_run_delegates_compiled_contract_to_executor(monkeypatch):
    from mag import roadmap_runner as rr

    contract = {"ok": True, "config_path": "memory/working/test.yaml", "branch_prefix": "mag/roadmap-v5-gate", "goal": "goal"}
    monkeypatch.setattr(rr, "select_next", lambda **kw: {"ok": True})
    monkeypatch.setattr(rr, "compile_run", lambda selection: contract)
    seen = {}
    monkeypatch.setattr(rr, "execute_contract", lambda value, **kw: seen.update({"contract": value, **kw}) or {"ok": True})
    out = rr.run_next(max_ticks=7)
    assert out["ok"] is True
    assert seen["contract"] == contract
    assert seen["timeout"] == 210


def test_execute_contract_verifies_commits_and_records_gate(tmp_path, monkeypatch):
    from mag import roadmap_runner as rr

    monkeypatch.setattr(rr, "ROOT", tmp_path)
    monkeypatch.setattr("mag.factory_machine.checkout_run_branch", lambda **kw: {"ok": True, "branch": "mag/roadmap-v5-g"})
    monkeypatch.setattr("mag.operating_protocol.build_envelope", lambda *a, **k: {"execution": {"provider": "deepseek"}})
    monkeypatch.setattr("mag.orchestrator.spawn_task", lambda *a, **k: {"ok": True, "task_id": "t1", "status": "running"})
    monkeypatch.setattr("mag.orchestrator.task_status", lambda tid: {"task_id": tid, "status": "done", "provider": "deepseek"})
    commands = []

    def fake_command(*args, **kwargs):
        commands.append(args)
        if args[:4] == ("git", "diff", "--cached", "--quiet"):
            return {"ok": False, "returncode": 1}
        return {"ok": True, "returncode": 0, "stdout_tail": "472 passed", "stderr_tail": ""}

    monkeypatch.setattr(rr, "_run_command", fake_command)
    recorded = {}
    monkeypatch.setattr("mag.release_registry.record_gate", lambda *a, **k: recorded.update({"args": a, **k}) or {"ok": True})
    contract = {
        "selection": {"version": "v5", "gate": {"id": "gstd_t0_probe"}},
        "goal": "[build] use queue/handoff/BUILD-roadmap-v5-gstd-t0-probe.md",
        "build_path": "queue/handoff/BUILD-roadmap-v5-gstd-t0-probe.md",
        "config_path": "memory/working/x.yaml",
        "evidence_path": "memory/runs/roadmap/v5-gstd_t0_probe.json",
        "branch_prefix": "mag/roadmap-v5-gstd",
    }
    out = rr.execute_contract(contract, timeout=30)
    assert out["ok"] is True
    assert (tmp_path / contract["evidence_path"]).is_file()
    assert any(cmd[:2] == ("git", "commit") for cmd in commands)
    assert recorded["args"] == ("v5", "gstd_t0_probe")
