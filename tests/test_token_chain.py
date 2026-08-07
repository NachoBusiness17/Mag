"""Token-chain: DeepSeek plan parse + local deterministic exec (no live API required)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_parse_and_execute_fixture(tmp_path, monkeypatch):
    from mag import token_chain as tc

    monkeypatch.setattr(tc, "RUN_DIR", tmp_path / "token_chain")
    # point safe paths at real improve files under ROOT
    order = tc.parse_work_order(
        json.dumps(
            {
                "schema": "local_work_order.v1",
                "goal": "test",
                "success_criteria": "ok",
                "steps": [
                    {"op": "read_file", "path": "memory/improve/field_brief.md"},
                    {"op": "count_lines", "path": "memory/improve/candidates.jsonl"},
                    {"op": "write_run_note", "note": "unit test note"},
                ],
            }
        )
    )
    assert order["schema"] == "local_work_order.v1"
    assert len(order["steps"]) == 3
    res = tc.execute_work_order(order)
    assert res["ok"] is True
    assert res["n_ok"] == 3
    assert (tmp_path / "token_chain" / "local_note.md").is_file()


def test_reject_unsafe_path():
    from mag import token_chain as tc
    import pytest

    with pytest.raises(ValueError):
        tc.parse_work_order(
            json.dumps(
                {
                    "schema": "local_work_order.v1",
                    "goal": "x",
                    "steps": [{"op": "read_file", "path": "../.env"}],
                }
            )
        )


def test_reject_unknown_op():
    from mag import token_chain as tc
    import pytest

    with pytest.raises(ValueError):
        tc.parse_work_order(
            json.dumps(
                {
                    "schema": "local_work_order.v1",
                    "goal": "x",
                    "steps": [{"op": "rm_rf", "path": "memory/improve"}],
                }
            )
        )


def test_dry_run_chain(tmp_path, monkeypatch):
    from mag import token_chain as tc

    monkeypatch.setattr(tc, "RUN_DIR", tmp_path / "token_chain")
    out = tc.run_token_chain(goal="dry unit", dry=True, live=False)
    assert out.get("execution", {}).get("ok") is True
    assert out["token_thesis"]["local_llm_tokens"] == 0
    assert (tmp_path / "token_chain" / "latest.json").is_file()


def test_rest_handler_dry(tmp_path, monkeypatch):
    from mag import token_chain as tc
    from dashboard.rest import h_token_chain

    monkeypatch.setattr(tc, "RUN_DIR", tmp_path / "token_chain")
    code, body = h_token_chain({}, {"goal": "rest dry", "dry": True})
    assert code == 200
    assert body.get("execution", {}).get("ok") is True
    code2, body2 = h_token_chain({}, None)
    assert code2 == 200
    assert body2.get("latest") is not None
