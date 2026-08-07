import json

from mag.cost_ledger import emit_terminal, task_estimate


def test_task_estimate_has_frozen_contract():
    row = task_estimate("[build] proof", provider="deepseek", model="deepseek-chat")
    assert row["schema"] == "task_estimate.v1"
    assert row["seat"] == "deepseek"
    assert row["price_band_usd"] >= 0


def test_terminal_ledger_joins_estimate_actual_and_outcome(tmp_path):
    ledger = tmp_path / "cost_ledger.jsonl"
    queue = {
        "queue_id": "q1", "task_id": "t1", "goal": "test proof", "provider": "deepseek",
        "model": "deepseek-chat", "usage_started_at": "2026-08-06T10:00:00+00:00",
        "task_estimate": {"schema": "task_estimate.v1", "price_band_usd": 0.01, "seat": "deepseek"},
    }
    task = {"task_id": "t1", "status": "done", "ended_at": "2026-08-06T10:01:00+00:00"}
    usage = [{"ts": "2026-08-06T10:00:30+00:00", "provider": "deepseek", "prompt_tokens": 1000, "completion_tokens": 500}]
    result = emit_terminal(queue, task, usage_rows=usage, ledger_path=ledger)
    assert result["ok"] and result["row"]["actual"]["calls"] == 1
    assert result["row"]["join"] == {"queue_id": "q1", "task_id": "t1", "session_id": "orc-t1"}
    assert result["row"]["outcome"]["leaf_kind"] == "test"
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1
    again = emit_terminal(queue, task, usage_rows=usage, ledger_path=ledger)
    assert again["action"] == "already_filed"
    assert json.loads(ledger.read_text(encoding="utf-8"))["schema"] == "cost_ledger.v1"
