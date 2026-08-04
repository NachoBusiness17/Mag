"""Phase 3 loop-killers: read_file line-range addressing + write_file .py auto-verify.

Coverage (mirrors memory/improve/session-loop-mining-2026-08-03.md asks #1/#2):
- read_file line_from/line_to numbered region, clamping, EOF extension
- write_file diff + full on .py -> verified/compile_error/changed_from/changed_to
- non-.py writes untouched; drift guard and uniqueness still enforced
"""
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from tools.filesystem import read_file, write_file

GOOD_PY = "def f(x):\n    return x + 1\n"
BAD_PY = "def f(:\n    return x + 1\n"


@pytest.fixture()
def tmpfile():
    d = Path(tempfile.mkdtemp(prefix="phase3_", dir=Path(".")))
    f = d / "sample.py"
    f.write_text(GOOD_PY, encoding="utf-8")
    yield f
    import shutil

    shutil.rmtree(d, ignore_errors=True)


def test_read_full_still_works(tmpfile):
    r = read_file(str(tmpfile))
    assert r["ok"] is True
    assert "def f" in r["output"]
    assert r["total_lines"] == 2
    assert len(r["sha256"]) == 64


def test_read_line_range_numbered(tmpfile):
    r = read_file(str(tmpfile), line_from=2, line_to=2)
    assert r["ok"] is True
    assert r["lines"] == ["2:     return x + 1"]
    assert r["line_from"] == 2 and r["line_to"] == 2
    assert r["total_lines"] == 2


def test_read_line_from_only_extends_to_eof(tmpfile):
    r = read_file(str(tmpfile), line_from=2)
    assert r["ok"] is True
    assert r["line_to"] == 2  # clamped to EOF
    assert r["lines"][0].startswith("2:")


def test_read_range_clamps_overrun(tmpfile):
    r = read_file(str(tmpfile), line_from=1, line_to=99)
    assert r["ok"] is True
    assert r["line_to"] == 2  # clamped, not an error
    assert len(r["lines"]) == 2


def test_write_diff_py_verified(tmpfile):
    r = write_file(str(tmpfile), search="return x + 1", replace="return x + 2")
    assert r["ok"] is True
    assert r["mode"] == "diff"
    assert r["verified"] is True
    assert r["changed_from"] == 2 and r["changed_to"] == 2
    assert "compile_error" not in r


def test_write_diff_py_syntax_error_detected(tmpfile):
    r = write_file(str(tmpfile), search="return x + 1", replace="return x +")
    assert r["ok"] is True  # the write happened
    assert r["verified"] is False
    assert "compile_error" in r
    assert "changed_from" in r  # still tells you where to re-read


def test_write_full_py_verified(tmpfile):
    r = write_file(str(tmpfile), content="x = 1\n")
    assert r["ok"] is True
    assert r["mode"] == "full"
    assert r["verified"] is True


def test_write_full_py_syntax_error_detected(tmpfile):
    r = write_file(str(tmpfile), content=BAD_PY)
    assert r["ok"] is True
    assert r["verified"] is False
    assert "compile_error" in r


def test_write_md_no_verify_key(tmpfile):
    md = tmpfile.with_suffix(".md")
    md.write_text("hello\n", encoding="utf-8")
    r = write_file(str(md), search="hello", replace="world")
    assert r["ok"] is True
    assert "verified" not in r


def test_drift_guard_still_rejects(tmpfile):
    r = write_file(str(tmpfile), search="x + 1", replace="x + 9", snapshot="0" * 64)
    assert r["ok"] is False
    assert "DRIFT" in r["error"]


def test_uniqueness_still_enforced(tmpfile):
    tmpfile.write_text("a = 1\na = 1\n", encoding="utf-8")
    r = write_file(str(tmpfile), search="a = 1", replace="a = 2")
    assert r["ok"] is False
    assert "ambiguous" in r["error"]
