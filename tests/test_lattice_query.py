"""Lattice query store — load, theme filter, neighbors, summary."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def lattice_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import mag.lattice_query as lq

    store = tmp_path / "memory" / "lattice"
    store.mkdir(parents=True)
    nodes = [
        {
            "schema": "lattice_node.v1",
            "id": "knot:2026-08-01_test",
            "kind": "session_knot",
            "session_id": "sess-a",
            "dominant_theme": "mag_hands",
            "date": "2026-08-01",
        },
        {
            "schema": "lattice_node.v1",
            "id": "dig:c0002_layer_five_step",
            "kind": "instrument_dig",
            "unit_id": "layer_five_step",
            "cycle": 2,
        },
        {
            "schema": "lattice_node.v1",
            "id": "bond:mag-companion",
            "kind": "residual_bond",
            "text": "Mag companion bond",
        },
    ]
    edges = [
        {
            "schema": "lattice_edge.v1",
            "id": "edge:session_dig:knot->dig",
            "kind": "session_dig",
            "source": "knot:2026-08-01_test",
            "target": "dig:c0002_layer_five_step",
            "weight": 0.35,
        },
        {
            "schema": "lattice_edge.v1",
            "id": "edge:bond:knot->bond",
            "kind": "residual_bond",
            "source": "knot:2026-08-01_test",
            "target": "bond:mag-companion",
            "weight": 0.4,
        },
    ]
    (store / "nodes.jsonl").write_text(
        "\n".join(json.dumps(n) for n in nodes) + "\n",
        encoding="utf-8",
    )
    (store / "edges.jsonl").write_text(
        "\n".join(json.dumps(e) for e in edges) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lq, "LATTICE_DIR", store)
    monkeypatch.setattr(lq, "NODES_PATH", store / "nodes.jsonl")
    monkeypatch.setattr(lq, "EDGES_PATH", store / "edges.jsonl")
    return store


def test_load_nodes_edges(lattice_store):
    from mag.lattice_query import load_edges, load_nodes

    assert len(load_nodes()) == 3
    assert len(load_edges()) == 2


def test_query_by_theme(lattice_store):
    from mag.lattice_query import query_by_theme

    hits = query_by_theme("mag_hands")
    assert len(hits) == 1
    assert hits[0]["id"] == "knot:2026-08-01_test"


def test_neighbors(lattice_store):
    from mag.lattice_query import neighbors

    n = neighbors("knot:2026-08-01_test")
    assert len(n["edges"]) == 2
    assert len(n["nodes"]) == 2
    kinds = {x["kind"] for x in n["nodes"]}
    assert kinds == {"instrument_dig", "residual_bond"}


def test_summary(lattice_store):
    from mag.lattice_query import summary

    s = summary()
    assert s["ok"] is True
    assert s["node_count"] == 3
    assert s["edge_count"] == 2
    assert s["kinds"]["session_knot"] == 1
    assert s["theme_histogram"]["mag_hands"] == 1


def test_parse_dig_meta_from_name():
    from mag.lattice_backfill import parse_dig_meta

    class P:
        name = "c0007_url_7.md"

        def read_text(self, encoding="utf-8", errors="replace"):
            return "# Lattice dig `url_7` cycle 7\n\n- pack: `p1`\n- urls: []\n"

    meta = parse_dig_meta(P())  # type: ignore[arg-type]
    assert meta["cycle"] == 7
    assert meta["unit_id"] == "url_7"
    assert meta["pack_id"] == "p1"
