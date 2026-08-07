"""Roadmap gap probe — O/S/G/A/T auditor vs disk + optional live dashboard.

Run:
  python scripts/roadmap_gap_probe.py
  python scripts/roadmap_gap_probe.py --live
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_JSON = ROOT / "memory" / "improve" / "roadmap_gap_report.json"
OUT_YAML = ROOT / "memory" / "improve" / "roadmap_audit.yaml"
REST = ROOT / "dashboard" / "rest.py"
BASE = "http://127.0.0.1:8765"


def _http_get_json(url: str, timeout: float = 4.0) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace")), None
    except Exception as e:
        return None, str(e)


def _gate(pass_fn) -> str:
    return "pass" if pass_fn() else "fail"


def _file_exists(rel: str) -> bool:
    return (ROOT / rel).is_file()


def _rest_has(route: str) -> bool:
    if not REST.is_file():
        return False
    return route in REST.read_text(encoding="utf-8", errors="replace")


def _training_pattern_counts() -> dict[str, int]:
    path = ROOT / "memory" / "training" / "events.jsonl"
    counts: dict[str, int] = {}
    if not path.is_file():
        return counts
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            p = str(row.get("pattern") or "?")
            counts[p] = counts.get(p, 0) + 1
        except json.JSONDecodeError:
            continue
    return counts


ROADMAP_ITEMS: list[dict[str, Any]] = [
    {
        "id": "desk",
        "title": "Agent Desk calibration",
        "observe": lambda: _rest_has("/api/v1/desk-dialogue") and _file_exists("memory/working/agent_desk.md"),
        "steer": lambda: _rest_has("post_desk_steer") or _rest_has("steer_context"),
        "graduate": lambda: _read_trust_tier() >= 0,
        "audit": lambda: _file_exists("prompts/desk_dialogue_etiquette.txt"),
        "train": lambda: _training_pattern_counts().get("skill_gate", 0) >= 0,
    },
    {
        "id": "stack",
        "title": "Stack viewport",
        "observe": lambda: _rest_has("/api/v1/stack"),
        "steer": lambda: True,
        "graduate": lambda: _file_exists("mag/stack.py"),
        "audit": lambda: True,
        "train": lambda: True,
    },
    {
        "id": "v3-007",
        "title": "Spider meta-supervisor",
        "observe": lambda: _file_exists("mag/spider.py"),
        "steer": lambda: _file_exists("memory/runs/spider_trail.jsonl") or True,
        "graduate": lambda: False,
        "audit": lambda: True,
        "train": lambda: _training_pattern_counts().get("spider_signal", 0) > 0,
    },
    {
        "id": "v3-009",
        "title": "L-conductor",
        "observe": lambda: _file_exists("mag/conductor.py"),
        "steer": lambda: True,
        "graduate": lambda: False,
        "audit": lambda: _file_exists("configs/training_patterns.yaml"),
        "train": lambda: _training_pattern_counts().get("route_decision", 0) > 0,
    },
    {
        "id": "v3-008",
        "title": "Resonance lens",
        "observe": lambda: _file_exists("mag/resonance.py"),
        "steer": lambda: False,
        "graduate": lambda: False,
        "audit": lambda: True,
        "train": lambda: _training_pattern_counts().get("resonance_hit", 0) > 0,
    },
    {
        "id": "v3-005",
        "title": "Training export + eval",
        "observe": lambda: _file_exists("mag/training_events.py"),
        "steer": lambda: True,
        "graduate": lambda: _file_exists("configs/training_patterns.yaml"),
        "audit": lambda: True,
        "train": lambda: _file_exists("memory/training/events.jsonl"),
    },
    {
        "id": "ponytail-caveman",
        "title": "Skill seats + gates",
        "observe": lambda: _file_exists("mag/skill_seat.py"),
        "steer": lambda: True,
        "graduate": lambda: False,
        "audit": lambda: _file_exists("configs/skills.yaml"),
        "train": lambda: _training_pattern_counts().get("skill_gate", 0) > 0,
    },
    {
        "id": "autorun",
        "title": "Autorun fill/drain",
        "observe": lambda: _file_exists("mag/governor_autorun.py"),
        "steer": lambda: True,
        "graduate": lambda: _autorun_trust_gate(),
        "audit": lambda: True,
        "train": lambda: _training_pattern_counts().get("autorun_cycle", 0) > 0,
    },
]


def _read_trust_tier() -> int:
    path = ROOT / "memory" / "working" / "agent_desk_trust_status.json"
    if not path.is_file():
        return 0
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("tier") or 0)
    except Exception:
        return 0


def _autorun_trust_gate() -> bool:
    src = (ROOT / "mag" / "governor_autorun.py").read_text(encoding="utf-8", errors="replace")
    return "trust_blocked" in src


def score_item(item: dict[str, Any]) -> dict[str, Any]:
    gates = {}
    for key in ("observe", "steer", "graduate", "audit", "train"):
        fn = item.get(key)
        gates[key] = bool(fn()) if callable(fn) else False
    n_pass = sum(1 for v in gates.values() if v)
    if n_pass >= 5:
        color = "green"
    elif gates.get("observe"):
        color = "yellow"
    else:
        color = "red"
    gaps = [k for k, v in gates.items() if not v]
    return {
        "id": item["id"],
        "title": item["title"],
        "gates": gates,
        "score": f"{n_pass}/5",
        "color": color,
        "gaps": gaps,
    }


def live_checks() -> dict[str, Any]:
    out: dict[str, Any] = {"dashboard_up": False}
    alive, err = _http_get_json(f"{BASE}/api/v1/desk-dialogue")
    out["desk_dialogue_error"] = err
    if alive:
        out["dashboard_up"] = True
        out["desk_api_live"] = alive.get("desk_api")
        out["desk_api_code"] = "handoff_loop.v1"
        out["desk_api_match"] = alive.get("desk_api") == "handoff_loop.v1"
        if not out["desk_api_match"]:
            out["desk_api_fix"] = "Restart lab — running dashboard is stale (Ctrl+C python main.py lab, relaunch)"
    stack, err_s = _http_get_json(f"{BASE}/api/v1/stack?limit=5")
    out["stack_error"] = err_s
    if stack and stack.get("ok"):
        out["stack_research_n"] = len(stack.get("research") or [])
        out["stack_desk_trust"] = stack.get("desk_trust")
    ui = None
    try:
        from scripts.desk_baseline_probe import run_desk_ui_smoke

        ui = run_desk_ui_smoke()
        passed = sum(1 for r in ui if r.get("pass"))
        out["ui_smoke"] = f"{passed}/{len(ui)}"
        out["ui_smoke_failures"] = [r for r in ui if not r.get("pass")]
    except Exception as e:
        out["ui_smoke_error"] = str(e)
    return out


def main() -> int:
    live = "--live" in sys.argv or "-l" in sys.argv
    items = [score_item(it) for it in ROADMAP_ITEMS]
    patterns = _training_pattern_counts()

    try:
        from mag.desk_dialogue import desk_health_check

        desk_health = desk_health_check(auto_heal=False)
    except Exception as e:
        desk_health = {"error": str(e)}

    try:
        from mag.stack import build_stack_payload

        stack = build_stack_payload(feed_limit=5, agent_limit=5)
    except Exception as e:
        stack = {"error": str(e)}

    try:
        from mag.governor_autorun import fill_queue

        fill = fill_queue(max_improve=0, max_state=0, max_handoff=0, max_verkle=0)
    except Exception as e:
        fill = {"error": str(e)}

    report: dict[str, Any] = {
        "schema": "roadmap_gap_report.v1",
        "items": items,
        "training_patterns": patterns,
        "desk_health": desk_health,
        "stack_headline": stack.get("headline") if isinstance(stack, dict) else None,
        "stack_research": stack.get("research") if isinstance(stack, dict) else None,
        "autorun_fill_probe": {
            "trust_blocked": fill.get("trust_blocked"),
            "trust_reason": fill.get("trust_reason"),
        },
        "summary": {
            "green": sum(1 for i in items if i["color"] == "green"),
            "yellow": sum(1 for i in items if i["color"] == "yellow"),
            "red": sum(1 for i in items if i["color"] == "red"),
        },
    }
    if live:
        report["live"] = live_checks()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    yaml_lines = [
        "# Roadmap auditor scores — O/S/G/A/T (generated by roadmap_gap_probe.py)",
        f"# green={report['summary']['green']} yellow={report['summary']['yellow']} red={report['summary']['red']}",
        "",
    ]
    for it in items:
        yaml_lines.append(f"{it['id']}:")
        yaml_lines.append(f"  title: {it['title']}")
        yaml_lines.append(f"  color: {it['color']}")
        yaml_lines.append(f"  score: {it['score']}")
        yaml_lines.append(f"  gaps: [{', '.join(it['gaps'])}]")
        yaml_lines.append("")

    OUT_YAML.write_text("\n".join(yaml_lines), encoding="utf-8")

    print(json.dumps({"ok": True, "report": str(OUT_JSON), "audit": str(OUT_YAML), "summary": report["summary"]}, indent=2))
    for it in items:
        mark = {"green": "OK", "yellow": "~~", "red": "XX"}[it["color"]]
        print(f"  [{mark}] {it['id']:16} {it['score']}  gaps={','.join(it['gaps']) or '-'}")
    if live and report.get("live"):
        lv = report["live"]
        print(f"\nLive: dashboard={'UP' if lv.get('dashboard_up') else 'DOWN'} ui_smoke={lv.get('ui_smoke')}")
        if lv.get("desk_api_match") is False:
            print(f"  FIX: {lv.get('desk_api_fix')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
