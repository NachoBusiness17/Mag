"""Nervous system subsystem — no network required for schema/face tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import nervous_system as ns


def test_build_glance_schema_and_face(tmp_path, monkeypatch):
    # isolate face writes into tmp by patching FACE paths
    monkeypatch.setattr(ns, "FACE_MD", tmp_path / "nervous_system.md")
    monkeypatch.setattr(ns, "FACE_JSON", tmp_path / "nervous_system.json")
    g = ns.build_glance(write=True)
    assert g.get("schema") == "nervous_system.v1"
    assert "body" in g
    assert "session_tip" in g
    assert "agent_tip" in g
    assert isinstance(g.get("keys"), list)
    assert g["keys"]
    for row in g["keys"]:
        assert "status" in row
        assert row["status"] in ("ok", "env-only", "process-only", "missing", "empty-value")
        # never leak secrets
        assert "value" not in row
        assert "secret" not in json.dumps(row).lower()
    assert ns.FACE_MD.is_file()
    assert ns.FACE_JSON.is_file()
    text = ns.FACE_MD.read_text(encoding="utf-8")
    assert "Never print key values" in text or "not model memory" in text
    assert "sk-" not in text


def test_pack_excerpt_compact():
    ex = ns.pack_excerpt()
    assert ex.get("schema") == "nervous_system.v1"
    assert "keys_line" in ex
    assert "body" in ex


def test_format_glance_text():
    t = ns.format_glance_text()
    assert "Mag nervous" in t or "nervous" in t.lower()
    assert "keys:" in t
