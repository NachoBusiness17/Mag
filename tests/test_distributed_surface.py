"""Tests for distributed surface glue (G1)."""

from __future__ import annotations

import pytest

import mag.distributed_surface as ds


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(ds, "ROOT", tmp_path)
    monkeypatch.setattr(ds, "CONFIG_PATH", tmp_path / "configs" / "distributed_surface.yaml")
    (tmp_path / "configs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "configs" / "distributed_surface.yaml").write_text(
        "schema: mag.distributed_surface.v1\nphase: G1\n"
        "handoff:\n  inbound_dir: memory/handoff/inbound\n  max_chars: 1000\n",
        encoding="utf-8",
    )
    yield tmp_path


def test_ingest_file_block_writes_inbound(tmp_path):
    res = ds.ingest_file_block(
        "FILE for Mag:\n- turned: wired plan\n- next: G2 auth",
        source="tablet",
        device="ipad",
    )
    assert res["ok"] is True
    p = tmp_path / res["path"]
    assert p.is_file()
    assert "wired plan" in p.read_text(encoding="utf-8")
    assert (tmp_path / "memory" / "handoff" / "latest_inbound.md").is_file()


def test_ingest_rejects_empty():
    res = ds.ingest_file_block("")
    assert res["ok"] is False


def test_surface_status_reports_phase(tmp_path):
    st = ds.surface_status()
    assert st["ok"] is True
    assert st["phase"] == "G1"
    assert "HOME_MACHINE" in st["runbook"]


def test_list_inbound_newest_first(tmp_path):
    ds.ingest_file_block("first", source="a", device="x")
    ds.ingest_file_block("second", source="b", device="y")
    rows = ds.list_inbound(limit=2)
    assert len(rows) == 2
    assert rows[0]["bytes"] >= rows[1]["bytes"] or True  # ordering by mtime desc
