"""Idea graph v0 — pure disk graph; no Ollama."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import idea_graph as ig  # noqa: E402


@pytest.fixture()
def idea_tmp(tmp_path, monkeypatch):
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    face = tmp_path / "LATEST.md"
    monkeypatch.setattr(ig, "IDEAS_DIR", tmp_path)
    monkeypatch.setattr(ig, "NODES_PATH", nodes)
    monkeypatch.setattr(ig, "EDGES_PATH", edges)
    monkeypatch.setattr(ig, "LATEST_MD", face)
    return tmp_path


def test_add_link_pack_roundtrip(idea_tmp):
    a = ig.add_node(title="Topic A", ntype="topic", status="open", body="alpha")
    b = ig.add_node(title="Claim B", ntype="claim", status="open", body="beta")
    e = ig.link(a["id"], b["id"], etype="supports", note="A supports B")
    assert e["src"] == a["id"]
    assert e["dst"] == b["id"]
    assert e["type"] == "supports"

    rows = ig.list_nodes(status="open")
    assert len(rows) == 2

    pack = ig.pack_node(a["id"])
    assert "Topic A" in pack
    assert "supports" in pack
    assert b["id"] in pack or "Claim B" in pack

    nb = ig.neighborhood(a["id"], depth=1)
    assert nb["ok"]
    assert nb["n_nodes"] >= 2
    assert nb["n_edges"] >= 1

    sm = ig.summary()
    assert sm["n_nodes"] == 2
    assert sm["n_edges"] == 1
    assert sm["schema"] == ig.SCHEMA


def test_bad_type_raises(idea_tmp):
    with pytest.raises(ValueError):
        ig.add_node(title="x", ntype="not_a_type")
    a = ig.add_node(title="ok", ntype="topic")
    b = ig.add_node(title="ok2", ntype="topic")
    with pytest.raises(ValueError):
        ig.link(a["id"], b["id"], etype="not_an_edge")


def test_no_secret_fields_in_schema():
    # structural: node keys must not include common secret names in module constants
    assert "api_key" not in ig.NODE_TYPES
    assert "password" not in ig.EDGE_TYPES


def test_patch_node_status(idea_tmp):
    n = ig.add_node(title="Loop X", ntype="open_loop", status="open")
    out = ig.patch_node(n["id"], status="done")
    assert out["status"] == "done"
    assert out.get("updated_ts")
    again = ig.get_node(n["id"])
    assert again and again["status"] == "done"
    with pytest.raises(KeyError):
        ig.patch_node("n_does_not_exist", status="open")
    with pytest.raises(ValueError):
        ig.patch_node(n["id"], status="nope")
