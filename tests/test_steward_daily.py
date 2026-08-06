import json

import mag.steward as steward


def test_daily_preview_is_local_and_single_outcome(tmp_path, monkeypatch):
    monkeypatch.setattr(steward, "STEWARD_ROOT", tmp_path)
    result = steward.run_steward_daily(dry=True)
    assert result["schema"] == "steward_daily.v1"
    assert result["provider"] == "local-deterministic"
    assert result["remote_calls"] == 0
    assert len(result["outcomes"]) == 1


def test_daily_files_once_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(steward, "STEWARD_ROOT", tmp_path)
    first = steward.run_steward_daily(dry=False)
    second = steward.run_steward_daily(dry=False)
    assert first["action"] == "filed"
    assert second["action"] == "already_filed"
    files = list((tmp_path / "daily").glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert len(data["outcomes"]) == 1


def test_steward_goal_executes_daily_job(tmp_path, monkeypatch):
    monkeypatch.setattr(steward, "STEWARD_ROOT", tmp_path)
    result = steward.execute_steward_goal("[steward] steward-daily — bounded local maintenance leaf")
    assert result["ok"] is True
    assert result["job_id"] == "steward-daily"
