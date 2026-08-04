"""Tests for distributed surface glue (G1) — canonical todo/working paths."""

from __future__ import annotations

import pytest

import mag.distributed_surface as ds


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(ds, "ROOT", tmp_path)
    monkeypatch.setattr(ds, "CONFIG_PATH", tmp_path / "configs" / "distributed_surface.yaml")
    monkeypatch.setattr(ds, "TODO_PATH", tmp_path / "queue" / "todo.md")
    (tmp_path / "configs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "configs" / "distributed_surface.yaml").write_text(
        "schema: mag.distributed_surface.v1\nphase: G1\n"
        "paths:\n  todo: queue/todo.md\n  working: memory/working.md\n"
        "handoff:\n  max_chars: 1000\n",
        encoding="utf-8",
    )
    yield tmp_path


def test_ingest_short_goal_to_todo(tmp_path):
    res = ds.ingest_file_block("wire G2 auth on LAN", source="tablet", device="ipad")
    assert res["ok"] is True
    assert res["routed"] == "todo"
    todo = (tmp_path / "queue" / "todo.md").read_text(encoding="utf-8")
    assert "[mag]" in todo
    assert "wire G2 auth" in todo


def test_ingest_file_block_to_working_and_next_move_todo(tmp_path):
    body = (
        "FILE for Mag:\n"
        "- turned: planned glue\n"
        "- open loops: auth\n"
        "- next move: add MAG_REMOTE_TOKEN middleware\n"
    )
    res = ds.ingest_file_block(body, source="tablet", device="ipad")
    assert res["ok"] is True
    assert res["routed"] == "file+todo"
    working = (tmp_path / "memory" / "working.md").read_text(encoding="utf-8")
    assert "FILE for Mag" in working
    todo = (tmp_path / "queue" / "todo.md").read_text(encoding="utf-8")
    assert "MAG_REMOTE_TOKEN" in todo


def test_ingest_rejects_empty():
    res = ds.ingest_file_block("")
    assert res["ok"] is False


def test_surface_status_reports_canonical_paths(tmp_path):
    st = ds.surface_status()
    assert st["ok"] is True
    assert st["paths"]["todo"] == "queue/todo.md"
    assert st["auth"]["token_env"] == "MAG_REMOTE_TOKEN"


def test_write_auth_localhost_skips(monkeypatch):
    monkeypatch.setenv("MAG_BIND_HOST", "127.0.0.1")
    ok, err = ds.check_write_auth({})
    assert ok is True
    assert err == ""


def test_write_auth_remote_requires_token(monkeypatch):
    monkeypatch.setenv("MAG_BIND_HOST", "0.0.0.0")
    monkeypatch.delenv("MAG_REMOTE_TOKEN", raising=False)
    monkeypatch.delenv("MAG_REMOTE_AUTH_DISABLE", raising=False)
    assert ds.write_auth_required() is True
    ok, err = ds.check_write_auth({})
    assert ok is False
    assert "MAG_REMOTE_TOKEN" in err


def test_write_auth_remote_accepts_bearer(monkeypatch):
    monkeypatch.setenv("MAG_BIND_HOST", "0.0.0.0")
    monkeypatch.setenv("MAG_REMOTE_TOKEN", "sekrit")
    ok, _ = ds.check_write_auth({"Authorization": "Bearer sekrit"})
    assert ok is True
    bad, _ = ds.check_write_auth({"Authorization": "Bearer nope"})
    assert bad is False
