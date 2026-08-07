"""Tests for Local desk adapter — move extraction and normalization."""
from __future__ import annotations

from mag import desk_local_adapter as la


def test_extract_move_line_from_heading_wrapper():
    edit = "### Local · title\nBlack plays 4... exd4"
    assert la.extract_move_line(edit) == "4... exd4"


def test_extract_move_line_from_backtick_reply():
    assert la.extract_move_line("Post exactly `4... exd4` please") == "4... exd4"


def test_canvas_quality_heading_only():
    assert la.canvas_quality("### Local · title\nBlack plays 4... exd4") == "move"
    assert la.canvas_quality("### Local · title\n") == "heading_only"


def test_normalize_from_reply_when_canvas_heading():
    canvas = "### Local · title\nBlack plays 4... exd4"
    reply = "Understood, I will post `4... exd4`"
    out, meta = la.normalize_local_canvas_edit(canvas, reply=reply)
    assert "4... exd4" in out
    assert meta["normalized"] is True
    assert meta["extracted_from"] in ("canvas", "reply")


def test_normalize_operator_note():
    note = 'Your entire next canvas edit must be exactly one line: "4... exd4"'
    out, meta = la.normalize_local_canvas_edit("### Local · title", operator_note=note)
    assert meta["quality_after"] == "move"
    assert "4... exd4" in out


def test_format_local_canvas():
    assert la.format_local_canvas("5. O-O") == "### Local · move\n5. O-O\n"
