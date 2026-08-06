"""Desk baseline + UI smoke probes — no live dashboard required."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.desk_baseline_probe import (  # noqa: E402
    EXPECTED_DESK_API,
    _canvas_has_structure,
    run_desk_ui_smoke,
    preserve_live_desk,
)


def _mock_json(responses: dict[str, dict]) -> callable:
    ordered = sorted(responses.items(), key=lambda kv: len(kv[0]), reverse=True)

    def get_json(url: str) -> tuple[dict | None, str | None]:
        for prefix, body in ordered:
            if url == prefix or url.startswith(prefix):
                return body, None
        return None, "unexpected url"

    return get_json


def test_canvas_has_structure():
    assert _canvas_has_structure("## Goal\n\nfoo\n\n## Dialogue\n")
    assert not _canvas_has_structure("# title only")


def test_ui_smoke_all_pass(tmp_path):
    index = tmp_path / "index.html"
    app_js = tmp_path / "app.js"
    index.write_text('<script src="/static/app.js?v=agent-desk-v17"></script>', encoding="utf-8")
    app_js.write_text(
        "initAgentDesk(); loadDeskManual(); deskCanvasView; desk-pane-label; Preview; Edit; "
        + EXPECTED_DESK_API,
        encoding="utf-8",
    )
    canvas = "## Goal\n\nTest\n\n## Dialogue\n\n"
    responses = {
        "http://127.0.0.1:8765/api/v1/desk-dialogue": {
            "ok": True,
            "desk_api": EXPECTED_DESK_API,
        },
        "http://127.0.0.1:8765/api/v1/desk-dialogue?manual=1": {
            "ok": True,
            "text": "# Agent Desk — Operator Manual\n\nEtiquette",
        },
        "http://127.0.0.1:8765/api/v1/desk-dialogue?user_model=1": {
            "ok": True,
            "text": "# First User Model\n\nBaseline",
        },
        "http://127.0.0.1:8765/api/v1/agent-desk": {
            "ok": True,
            "text": canvas,
            "path": "memory/working/agent_desk.md",
        },
    }
    results = run_desk_ui_smoke(
        get_json=_mock_json(responses),
        index_html=index,
        app_js=app_js,
    )
    assert len(results) == 7
    assert all(r.get("pass") for r in results), json.dumps(results, indent=2)


def test_ui_smoke_dashboard_down(tmp_path):
    index = tmp_path / "index.html"
    app_js = tmp_path / "app.js"
    index.write_text('<script src="/static/app.js?v=x"></script>', encoding="utf-8")
    app_js.write_text("initAgentDesk loadDeskManual deskCanvasView desk-pane-label", encoding="utf-8")

    def fail_json(_url: str) -> tuple[dict | None, str | None]:
        return None, "Connection refused"

    results = run_desk_ui_smoke(get_json=fail_json, index_html=index, app_js=app_js)
    api = next(r for r in results if r["test"] == "desk_ui_smoke_api_alive")
    assert api["pass"] is False
    assert api["error"]
    static = next(r for r in results if r["test"] == "desk_ui_smoke_static_assets")
    assert static["pass"] is True


def test_workflow_test_mode_is_visible_and_propagated():
    index = (ROOT / "dashboard" / "static" / "index.html").read_text(encoding="utf-8", errors="replace")
    app = (ROOT / "dashboard" / "static" / "app.js").read_text(encoding="utf-8", errors="replace")

    assert 'id="deskLocalMode"' in index
    assert "Workflow test" in index
    assert "local_mode: deskLocalMode()" in app
    assert "Ollama is not being tested" in app


def test_dashboard_navigation_groups_each_surface_semantically():
    index = (ROOT / "dashboard" / "static" / "index.html").read_text(encoding="utf-8", errors="replace")
    app = (ROOT / "dashboard" / "static" / "app.js").read_text(encoding="utf-8", errors="replace")

    for section in ("home", "projects", "history", "run", "library", "system"):
        assert f'data-dashboard-section="{section}"' in index
        assert f'data-dashboard-group="{section}"' in index
    for view in ("home", "sessions", "diary", "story", "verkle", "ideas", "ingest", "chat", "status", "orchestrate", "viewports", "stack", "blast", "flow", "board"):
        assert index.count(f'data-dashboard-view="{view}"') == 1
    assert "DASHBOARD_VIEW_SECTION" in app
    assert "wireDashboardNav()" in app


def test_days_timeline_constrains_graph_height():
    css = (ROOT / "dashboard" / "static" / "cli.css").read_text(encoding="utf-8", errors="replace")

    assert "#win-sessions .days-view-timeline" in css
    assert "flex: 1 1 0% !important" in css
    assert "#win-sessions .days-view-timeline > .days-split" in css


def test_verkle_lattice_is_a_readable_honest_continuity_layer():
    index = (ROOT / "dashboard" / "static" / "index.html").read_text(encoding="utf-8", errors="replace")
    tapestry = (ROOT / "dashboard" / "static" / "tapestry.js").read_text(encoding="utf-8", errors="replace")

    assert ">Verkle artifacts<" in index
    assert "not a cryptographic Verkle proof" in index
    assert "lattice: 0x33d6ff" in tapestry
    assert "return 0.16" in tapestry
    assert "wireframe: false" in tapestry
    assert 'id="btnTapLatticeFocus"' in index
    assert "setLatticeFocus(on)" in tapestry


def test_verkle_knot_is_an_agent_handoff_artifact():
    index = (ROOT / "dashboard" / "static" / "index.html").read_text(encoding="utf-8", errors="replace")
    app = (ROOT / "dashboard" / "static" / "app.js").read_text(encoding="utf-8", errors="replace")
    tapestry = (ROOT / "mag" / "tapestry.py").read_text(encoding="utf-8", errors="replace")

    assert 'id="btnDaysCopyKnot"' in index
    assert 'id="btnDaysRouteKnot"' in index
    assert "/api/v1/verkle-knots/" in app
    assert '"label": "Verkle knot artifact"' in tapestry


def test_days_lenses_are_globally_wired_and_story_is_restored():
    index = (ROOT / "dashboard" / "static" / "index.html").read_text(encoding="utf-8", errors="replace")
    app = (ROOT / "dashboard" / "static" / "app.js").read_text(encoding="utf-8", errors="replace")

    assert 'data-days-view="story">Story so far<' in index
    assert "try { wireDaysSubnav(); }" in app
    assert 'btn.dataset.daysWired === "1"' in app
    assert "renderDaysDiary(j)" in app
    assert "wireStoryFileButtons(dst)" in app


def test_desk_primary_action_uses_real_behavioral_router():
    index = (ROOT / "dashboard" / "static" / "index.html").read_text(encoding="utf-8", errors="replace")
    app = (ROOT / "dashboard" / "static" / "app.js").read_text(encoding="utf-8", errors="replace")

    assert ">Direct Mag<" in index
    assert "router chooses the cheapest capable seat" in index
    assert ">Route goal<" in index
    assert 'postJSON("/api/v1/decide"' in app
    assert '"/api/v1/route"' in app
    assert "launch: true, background: true" in app
    assert "setDeskCanvasMode(\"edit\")" in app


def test_preserve_live_desk_restores_existing_and_removes_probe_file(tmp_path):
    existing = tmp_path / "desk.md"
    created = tmp_path / "dialogue.jsonl"
    existing.write_text("operator board", encoding="utf-8")
    restore = preserve_live_desk((existing, created))

    existing.write_text("probe board", encoding="utf-8")
    created.write_text("probe row", encoding="utf-8")
    restore()
    restore()

    assert existing.read_text(encoding="utf-8") == "operator board"
    assert not created.exists()
