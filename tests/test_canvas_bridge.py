"""Canvas bridge — sync, list, load, REST smoke."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


CANVAS_TSX = '''\
const REPO_ROWS = [
  ["demo-repo", "Demo role", ":9999", "done"],
];

const TODO = [
  { id: "t1", content: "Test todo item", status: "pending" as const },
];

export default function DemoCanvas() {
  return (
    <Stack>
      <H1>Demo Canvas Title</H1>
      <Stat label="Demo stat" value="42" />
    </Stack>
  );
}
'''


@pytest.fixture
def canvas_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import mag.canvas_bridge as cb

    src = tmp_path / "canvases"
    src.mkdir()
    viewports = tmp_path / "memory" / "viewports"
    viewports.mkdir(parents=True)
    lattice = tmp_path / "memory" / "lattice"
    lattice.mkdir(parents=True)

    (src / "demo-canvas.canvas.tsx").write_text(CANVAS_TSX, encoding="utf-8")

    monkeypatch.setattr(cb, "VIEWPORTS_DIR", viewports)
    monkeypatch.setattr(cb, "LATTICE_NODES", lattice / "nodes.jsonl")
    monkeypatch.setattr(cb, "_canvas_sources", lambda: [src])
    return {"src": src, "viewports": viewports, "lattice": lattice}


def test_seed_bundled_viewports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import mag.canvas_bridge as cb

    bundled = tmp_path / "docs" / "ref" / "viewports"
    bundled.mkdir(parents=True)
    runtime = tmp_path / "memory" / "viewports"
    lattice = tmp_path / "memory" / "lattice"
    lattice.mkdir(parents=True)

    (bundled / "seed-board.json").write_text(
        json.dumps(
            {
                "schema": "canvas_viewport.v1",
                "id": "seed-board",
                "title": "Seed",
                "sections": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(cb, "BUNDLED_VIEWPORTS_DIR", bundled)
    monkeypatch.setattr(cb, "VIEWPORTS_DIR", runtime)
    monkeypatch.setattr(cb, "LATTICE_NODES", lattice / "nodes.jsonl")

    res = cb.seed_bundled_viewports()
    assert res["seeded_n"] == 1
    assert (runtime / "seed-board.json").is_file()

    again = cb.seed_bundled_viewports()
    assert again["seeded_n"] == 0


def test_sync_dry_run(canvas_env):
    from mag.canvas_bridge import sync_canvases

    res = sync_canvases(dry_run=True)
    assert res["ok"] is True
    assert res["dry_run"] is True
    assert res["found"] == 1
    assert "demo-canvas" in res["written"]
    assert not (canvas_env["viewports"] / "demo-canvas.json").is_file()


def test_sync_write_and_load(canvas_env):
    from mag.canvas_bridge import load_viewport, list_viewports, sync_canvases

    res = sync_canvases(dry_run=False)
    assert res["written_n"] == 1
    assert (canvas_env["viewports"] / "demo-canvas.json").is_file()

    rows = list_viewports()
    assert len(rows) == 1
    assert rows[0]["id"] == "demo-canvas"

    one = load_viewport("demo-canvas")
    assert one["ok"] is True
    vp = one["viewport"]
    assert vp["schema"] == "canvas_viewport.v1"
    assert vp["title"] == "Demo Canvas Title"
    kinds = {s["kind"] for s in vp["sections"]}
    assert "table" in kinds
    assert "todos" in kinds
    assert "stats" in kinds


def test_mag_ecosystem_manual_seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import mag.canvas_bridge as cb

    src = tmp_path / "canvases"
    src.mkdir()
    viewports = tmp_path / "memory" / "viewports"
    viewports.mkdir(parents=True)
    lattice = tmp_path / "memory" / "lattice"
    lattice.mkdir(parents=True)

    eco_path = src / "mag-ecosystem-deep-dive.canvas.tsx"
    eco_path.write_text("// stub\nexport default function MagEcosystemDeepDive() { return null; }\n", encoding="utf-8")

    monkeypatch.setattr(cb, "VIEWPORTS_DIR", viewports)
    monkeypatch.setattr(cb, "LATTICE_NODES", lattice / "nodes.jsonl")
    monkeypatch.setattr(cb, "_canvas_sources", lambda: [src])

    from mag.canvas_bridge import sync_canvases

    sync_canvases()
    data = json.loads((viewports / "mag-ecosystem-deep-dive.json").read_text(encoding="utf-8"))
    assert data["id"] == "mag-ecosystem-deep-dive"
    assert len(data["sections"]) >= 6
    table = next(s for s in data["sections"] if s.get("title") == "Repository puzzle pieces")
    assert table["rows"][0][0] == "local_sovereign_agent"


def test_lattice_upsert_preserves_existing(canvas_env):
    from mag.canvas_bridge import sync_canvases

    lattice_path = canvas_env["lattice"] / "nodes.jsonl"
    lattice_path.write_text(
        json.dumps({"schema": "lattice_node.v1", "id": "knot:keep-me", "kind": "session_knot"})
        + "\n",
        encoding="utf-8",
    )
    sync_canvases()
    lines = [json.loads(l) for l in lattice_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    kinds = [n.get("kind") for n in lines]
    assert "session_knot" in kinds
    assert "canvas_viewport" in kinds
    assert sum(1 for n in lines if n.get("id") == "knot:keep-me") == 1


def test_rest_handlers_smoke(canvas_env):
    from dashboard.rest import h_viewport_one, h_viewports, h_viewports_sync
    from mag.canvas_bridge import sync_canvases

    sync_canvases()

    st, body = h_viewports({}, None)
    assert st == 200
    assert body["ok"] is True
    assert body["count"] == 1

    st, body = h_viewport_one({"id": "demo-canvas"}, None)
    assert st == 200
    assert body["viewport"]["id"] == "demo-canvas"

    st, body = h_viewports_sync({}, None)
    assert st == 200
    assert body["written_n"] == 1

    st, body = h_viewport_one({"id": "missing-slug"}, None)
    assert st == 404
