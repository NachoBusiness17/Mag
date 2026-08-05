"""Tests for tool dispatch arg-shape defense (bug #2, 12h sovereign run).

Covers:
- nested single-key {"arguments": {...}} blob unwraps correctly (the exact
  shape that caused 13-15 consecutive write_file TypeErrors on 2026-08-03);
- binding TypeError returns an actionable error with expected params, so a
  model recovers on the FIRST attempt instead of looping to the collapse
  detector;
- flat sibling-param calls keep working (no regression).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import _expected_params, _normalize_args, dispatch


def _jail_dir() -> Path:
    """Temp dir INSIDE the repo jail (tmp_path is outside FS_ROOTS)."""
    d = Path(tempfile.mkdtemp(prefix="_dispatch_shape_", dir=ROOT))
    return d


def test_unwrap_nested_arguments_blob():
    d = _jail_dir()
    try:
        p = d / "a.txt"
        r = dispatch("write_file", {"arguments": {"path": str(p), "content": "hi"}})
        assert r["ok"] is True, r
        assert p.read_text(encoding="utf-8") == "hi"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_unwrap_arguments_as_json_string():
    # Harness captures a single `arguments` param value as raw TEXT, so a model
    # emitting one `arguments` param yields {"arguments": '{"path": ...}'} — a
    # JSON *string*, not a dict. _normalize_args must json.loads it (bug found
    # 2026-08-04: the isinstance-dict guard missed the string case, causing the
    # exact "unexpected keyword argument 'arguments'" loop).
    d = _jail_dir()
    try:
        p = d / "str.txt"
        import json as _json

        arg_str = _json.dumps({"path": str(p), "content": "from-string"})
        r = dispatch("write_file", {"arguments": arg_str})
        assert r["ok"] is True, r
        assert p.read_text(encoding="utf-8") == "from-string"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_unwrap_parameters_codex_style():
    d = _jail_dir()
    try:
        p = d / "codex.txt"
        r = dispatch("write_file", {"parameters": {"path": str(p), "content": "codex"}})
        assert r["ok"] is True, r
        assert p.read_text(encoding="utf-8") == "codex"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_unwrap_params_and_kwargs_synonyms():
    d = _jail_dir()
    try:
        for key in ("params", "kwargs"):
            p = d / f"{key}.txt"
            r = dispatch("write_file", {key: {"path": str(p), "content": key}})
            assert r["ok"] is True, r
            assert p.read_text(encoding="utf-8") == key
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_flat_sibling_params_still_work():
    d = _jail_dir()
    try:
        p = d / "b.txt"
        r = dispatch("write_file", {"path": str(p), "content": "flat"})
        assert r["ok"] is True, r
        assert p.read_text(encoding="utf-8") == "flat"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_binding_typeerror_is_actionable():
    # wrong key (the historical collapse signature: write_file(arguments=...))
    r = dispatch("write_file", {"arguments": "not-a-dict", "path": "x"})
    # two keys -> NOT unwrapped -> binding TypeError -> actionable error
    assert r["ok"] is False
    assert r["exit_code"] == 2
    assert "bad arguments for write_file" in r["error"]
    assert "path" in r["expected_params"]
    assert "content" in r["expected_params"]
    assert "never nest" in r["error"]


def test_missing_required_param_is_actionable():
    r = dispatch("write_file", {"content": "no path"})
    assert r["ok"] is False
    assert r["exit_code"] == 2
    assert "bad arguments for write_file" in r["error"]
    assert "path" in r["expected_params"]


def test_normalize_unknown_tool_returns_none():
    assert _normalize_args("nope", {}) is None


def test_expected_params_lists_flat_names():
    s = _expected_params("write_file")
    assert "path" in s
    assert "content" in s
