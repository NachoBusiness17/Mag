"""Tests for seat FILE → Verkle workday pipeline."""

from __future__ import annotations

import json

import pytest

from config import ROOT
from mag.chat_source import agent_bio_id, agent_session_path
from mag.distributed_surface import ingest_file_block
from mag.seat_file import file_block_to_messages, file_handoff, file_seat, seat_local_id


def test_file_block_to_messages_extracts_next_move():
    msgs = file_block_to_messages(
        "FILE for Mag:\n- turned: wired glue\n- next move: ship G2 auth\n",
        goal="",
    )
    assert len(msgs) == 2
    assert "ship G2 auth" in msgs[0]["content"]


def test_seat_local_id_namespaced():
    assert seat_local_id("ipad", source="tablet").startswith("tablet-")


def test_file_seat_writes_residual(tmp_path, monkeypatch):
    seat = "_pytest_seat_file"
    local = seat_local_id(seat, source="cloud")
    path = agent_session_path(local)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        res = file_seat(
            seat,
            messages=[
                {"role": "user", "content": "pytest seat file verkle"},
                {"role": "assistant", "content": "FILEd through seat_file module."},
            ],
            provider="cursor",
            source="cloud",
            use_llm=False,
            force=True,
        )
        assert res.get("ok"), res
        bio = res.get("bio_session_id")
        assert bio == agent_bio_id(local)
        residual = ROOT / "memory" / "biography" / "residual" / f"{bio}.json"
        assert residual.is_file()
    finally:
        if path.is_file():
            path.unlink()
        bio = agent_bio_id(local)
        for p in (
            ROOT / "memory" / "biography" / "residual" / f"{bio}.json",
            ROOT / "memory" / "biography" / f"{bio}.md",
        ):
            if p.is_file():
                p.unlink()


def test_ingest_file_block_auto_verkle_for_file_for_mag(monkeypatch):
    monkeypatch.setattr("mag.seat_file.file_handoff", lambda *a, **k: {"ok": True, "bio_session_id": "mag-agent-test"})
    res = ingest_file_block(
        "FILE for Mag:\n- turned: test\n- next move: verify leaf\n",
        source="tablet",
        device="ipad",
    )
    assert res.get("ok")
    assert "verkle" in res.get("routed", "")
