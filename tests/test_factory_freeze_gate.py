import mag.factory_gate as gate
import mag.orchestrator as orchestrator
from mag.conductor import conduct
from mag.orchestrator import enqueue, spawn_task


def test_non_build_work_does_not_require_contract():
    assert gate.check_frozen_build("summarize current status")["ok"] is True


def test_build_without_named_contract_defers_before_spawn():
    checked = gate.check_frozen_build("[build] implement the feature")
    assert checked["ok"] is False
    assert "frozen" in checked["reason"].lower()
    assert spawn_task("[build] implement the feature")["ok"] is False
    assert enqueue("[build] implement the feature")["ok"] is False


def test_named_draft_contract_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "HANDOFF", tmp_path)
    (tmp_path / "BUILD-demo.md").write_text("# BUILD demo\n\n**Status:** draft\n", encoding="utf-8")
    checked = gate.check_frozen_build("[build] use BUILD-demo.md")
    assert checked["ok"] is False
    assert "not frozen" in checked["reason"]


def test_frozen_contract_unlocks_conductor(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "HANDOFF", tmp_path)
    monkeypatch.setattr("mag.switchboard.route_intent", lambda goal, dry=False: {})
    monkeypatch.setattr("mag.router.route", lambda *args, **kwargs: {"seat": "agent", "provider": "deepseek", "depth": "deep"})
    (tmp_path / "BUILD-demo.md").write_text("# BUILD demo\n\n**Status:** frozen\n", encoding="utf-8")
    checked = gate.check_frozen_build("[build] use BUILD-demo.md")
    assert checked["ok"] is True
    assert checked["tier"] == "T1"
    result = conduct("[build] use BUILD-demo.md", dry=True)
    assert result["overlay"]["factory_gate"]["ok"] is True
    assert result["overlay"]["suggested_seat"] == "agent"


def test_frozen_contract_tier_is_propagated_to_agent_command(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "HANDOFF", tmp_path)
    (tmp_path / "BUILD-remote.md").write_text(
        "# BUILD remote\n\n**Status:** frozen\n**Tier:** T2\n", encoding="utf-8"
    )
    seen = {}

    def fake_spawn(cmd, **kwargs):
        seen["cmd"] = cmd
        return {"task_id": "test", "status": "running"}

    monkeypatch.setattr(orchestrator, "_running_tasks", lambda: [])
    monkeypatch.setattr(orchestrator, "_spawn_cmd", fake_spawn)
    monkeypatch.setattr("mag.autorun_common.refresh_context_for_goal", lambda goal: {})
    result = orchestrator.spawn_task("[build] use BUILD-remote.md", provider="deepseek")
    assert result["ok"] is True
    assert seen["cmd"][-2:] == ["--tier", "T2"]
