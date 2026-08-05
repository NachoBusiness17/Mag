"""Pack modes + steward-scope job."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_infer_pack_mode():
    from mag.context_pack import infer_pack_mode

    assert infer_pack_mode("[steward] steward-scope — x") == "janitor"
    assert infer_pack_mode("[build] implement foo") == "build"
    assert infer_pack_mode("[priority] plan arch") == "plan"
    assert infer_pack_mode("audit only diff review") == "audit"


def test_janitor_smaller_than_full():
    from mag.context_pack import build_context_pack, format_context_pack_text

    full = format_context_pack_text(build_context_pack(mode="full"))
    jan = format_context_pack_text(build_context_pack(mode="janitor"))
    assert len(jan) < len(full)
    assert "mode=janitor" in jan


def test_build_mode_includes_build_excerpt(tmp_path, monkeypatch):
    from mag import context_pack as cp

    build = tmp_path / "BUILD-test.md"
    build.write_text(
        "# BUILD test\n\n**Status:** frozen\n\n## Goal\nDo the thing.\n",
        encoding="utf-8",
    )
    pack = cp.build_context_pack(mode="build", build_path=build)
    assert pack.get("mode") == "build"
    assert "Do the thing" in (pack.get("build_excerpt") or "")
    text = cp.format_context_pack_text(pack, mode="build", max_chars=8000)
    assert "L2b Frozen BUILD" in text or "Do the thing" in text


def test_steward_scope_heuristic(tmp_path, monkeypatch):
    from mag import steward as st

    ref = tmp_path / "docs" / "ref"
    ref.mkdir(parents=True)
    (ref / "BUILD-pack-modes-janitor.md").write_text(
        """# BUILD — pack modes

**Status:** frozen
**Slug:** `pack-modes-janitor`

## Goal
Add mode= to context_pack.

## Scope

| In | Out |
|----|-----|
| context_pack.py | layman layout |

## Verify
pytest tests/test_pack_modes.py
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(st, "ROOT", tmp_path)
    monkeypatch.setattr(st, "SCOPE_DIR", tmp_path / "memory" / "steward" / "scope_cards")
    monkeypatch.setattr(st, "STEWARD_ROOT", tmp_path / "memory" / "steward")
    monkeypatch.setattr(st, "TRAIL", tmp_path / "memory" / "runs" / "steward_trail.jsonl")
    monkeypatch.setattr(st, "LAST_RUNS", tmp_path / "memory" / "steward" / "last_runs.json")
    monkeypatch.setattr(st, "RUN_DOC", tmp_path / "docs" / "ref" / "MAG_NEXT_CODING_RUN.md")

    res = st.run_steward_scope(dry=False, use_llm=False)
    assert res.get("ok") is True
    scope_path = tmp_path / "memory" / "steward" / "scope_cards" / "pack-modes-janitor.md"
    assert scope_path.is_file()
    body = scope_path.read_text(encoding="utf-8")
    assert "pack-modes-janitor" in body
    assert "[build]" in body


def test_steward_inline_spawn(tmp_path, monkeypatch):
    from mag import orchestrator as orc

    orc.TASK_DIR = tmp_path / "tasks"
    orc.TRAIL = tmp_path / "trail.jsonl"
    orc.TASK_DIR.mkdir(parents=True)

    monkeypatch.setattr(
        "mag.steward.execute_steward_goal",
        lambda goal, dry=False: {"ok": True, "job": "steward-patterns", "path": "/tmp/x"},
    )
    rec = orc.spawn_task("[steward] steward-patterns — daily", tag="test")
    assert rec.get("ok") is True
    assert rec.get("status") == "done"
    assert "steward" in rec.get("task_id", "")
