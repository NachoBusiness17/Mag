"""Agent state versioning — no Ollama."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_commit_chain_and_load(tmp_path, monkeypatch):
    import mag.agent_state as ast

    monkeypatch.setattr(ast, "STATE_DIR", tmp_path / "agent_state")
    monkeypatch.setattr(ast, "VERSIONS", tmp_path / "agent_state" / "versions")
    monkeypatch.setattr(ast, "CHAIN", tmp_path / "agent_state" / "chain.jsonl")
    monkeypatch.setattr(ast, "TIP", tmp_path / "agent_state" / "tip.json")
    monkeypatch.setattr(ast, "LATEST_JSON", tmp_path / "agent_state" / "LATEST.json")
    monkeypatch.setattr(ast, "LATEST_MD", tmp_path / "agent_state" / "LATEST.md")
    monkeypatch.setattr(ast, "ROOT", tmp_path)

    r1 = ast.commit_state(
        {
            "one_line": "first version",
            "do_not_redesign": ["DNA residual"],
            "compose_bundles": [{"id": "A", "line": "restful mag"}],
            "next_moves": [{"id": "m1", "title": "status face", "status": "open"}],
            "stack": {"raw": "empty"},
            "paths": {"x": "memory/foo"},
            "leave": ["tokens"],
        },
        label="v1",
        reason="test",
    )
    assert r1["ok"]
    c1 = r1["content_commit"]
    r2 = ast.commit_state(
        {
            "one_line": "second version",
            "do_not_redesign": ["DNA residual", "IJL sockets"],
            "next_moves": [{"id": "m1", "title": "status face", "status": "done"}],
            "stack": {"raw": "empty"},
            "paths": {},
            "leave": [],
        },
        label="v2",
        reason="test2",
    )
    assert r2["ok"]
    assert r2["parent_commit"] == c1
    assert r2["tip"]["n_versions"] == 2
    lat = ast.load_latest()
    assert lat and lat["label"] == "v2"
    assert "first" not in (lat.get("one_line") or "")
    # history intact
    old = ast.load_version(c1[:8])
    assert old and old["label"] == "v1"
    text = ast.format_load_markdown()
    assert "Anti-reinvention" in text
    assert "DNA residual" in text
    rows = ast.list_versions()
    assert len(rows) == 2


def test_pack_excerpt_empty(tmp_path, monkeypatch):
    import mag.agent_state as ast

    monkeypatch.setattr(ast, "LATEST_JSON", tmp_path / "missing.json")
    assert "no agent_state" in ast.pack_excerpt()
