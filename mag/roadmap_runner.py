"""Compile the next release-roadmap gate into a frozen factory run."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from config import ROOT

ROADMAP_PATH = ROOT / "configs" / "version_roadmap.yaml"
RELEASES_PATH = ROOT / "configs" / "releases.yaml"
BUILD_DIR = ROOT / "queue" / "handoff"
RUN_CONFIG_DIR = ROOT / "memory" / "working" / "roadmap_runs"
EVIDENCE_DIR = ROOT / "memory" / "runs" / "roadmap"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return data if isinstance(data, dict) else {}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")[:80]


def _passed(version: str) -> set[str]:
    from mag.release_registry import read_gate_log

    return {
        str(row.get("gate_id"))
        for row in read_gate_log(limit=1000, version=version)
        if row.get("ok") and row.get("gate_id")
    }


def select_next(*, version: str | None = None, gate: str | None = None) -> dict[str, Any]:
    """Select the first executable, unpassed release gate in roadmap order."""
    roadmap = _load(ROADMAP_PATH)
    registry = _load(RELEASES_PATH)
    arc = [row for row in roadmap.get("version_arc") or [] if isinstance(row, dict)]
    releases = {str(row.get("id")): row for row in registry.get("releases") or [] if isinstance(row, dict)}
    shipped = {str(row.get("id")) for row in arc if row.get("status") == "shipped"}

    for arc_row in arc:
        vid = str(arc_row.get("id") or "")
        if version and vid.lstrip("v") != str(version).lstrip("v"):
            continue
        status = str(arc_row.get("status") or "")
        if status == "shipped":
            continue
        if status == "curriculum_tbd":
            if version:
                return {"ok": False, "error": "curriculum_tbd", "version": vid, "reason": "Roadmap gates must be defined before autonomous execution."}
            continue
        rel = releases.get(vid) or {}
        parent = str(rel.get("parent") or "")
        if parent and parent not in shipped:
            return {"ok": False, "error": "parent_not_shipped", "version": vid, "parent": parent}
        gates = rel.get("gates")
        if not isinstance(gates, list) or not gates:
            return {"ok": False, "error": "gates_not_defined", "version": vid}
        passed = _passed(vid)
        for gate_row in gates:
            if not isinstance(gate_row, dict) or not gate_row.get("id"):
                continue
            gid = str(gate_row["id"])
            if gate and gid != gate:
                continue
            if gid in passed:
                continue
            sources = []
            for key in ("notes_path", "plan_path", "direction_path", "run_sheet_path", "mold_path", "pipe_path"):
                if rel.get(key):
                    sources.append(str(rel[key]))
            sources.extend(str(t.get("path")) for t in rel.get("tracks") or [] if isinstance(t, dict) and t.get("path"))
            return {
                "ok": True,
                "schema": "roadmap_selection.v1",
                "version": vid,
                "era": rel.get("era") or arc_row.get("era"),
                "meaning": arc_row.get("meaning") or rel.get("meaning") or "",
                "commitment": rel.get("commitment"),
                "gate": {**gate_row, "id": gid},
                "passed_gates": sorted(passed),
                "sources": sources,
            }
        if gate:
            return {"ok": False, "error": "gate_not_available", "version": vid, "gate": gate}
        return {"ok": False, "error": "release_has_no_remaining_gates", "version": vid}
    return {"ok": False, "error": "no_executable_roadmap_work"}


def compile_run(selection: dict[str, Any]) -> dict[str, Any]:
    if not selection.get("ok"):
        return selection
    vid = str(selection["version"])
    gate = dict(selection["gate"])
    gid = str(gate["id"])
    slug = f"{_slug(vid)}-{_slug(gid)}"
    build_path = BUILD_DIR / f"BUILD-roadmap-{slug}.md"
    config_path = RUN_CONFIG_DIR / f"{slug}.yaml"
    evidence_path = EVIDENCE_DIR / f"{slug}.json"
    sources = [s for s in selection.get("sources") or [] if (ROOT / s).is_file()]
    goal = (
        f"[build] Complete roadmap {vid} gate {gid} from the frozen contract at "
        f"queue/handoff/{build_path.name}. Use the cheapest capable worker, run the full test suite, "
        "file evidence, and stop only when the gate is verified or genuinely blocked."
    )
    source_lines = "\n".join(f"- `{s}`" for s in sources) or "- `configs/releases.yaml`"
    description = str(gate.get("description") or f"Implement and verify release gate {gid}.")
    verify = gate.get("verify") or []
    verify_lines = "\n".join(f"- {v}" for v in verify) if isinstance(verify, list) else ""
    build = f"""# BUILD — roadmap {vid} / {gid}

**Status:** frozen
**Tier:** T2
**Commitment:** `{selection.get('commitment') or vid}`
**Generated:** {_now()}

## Goal

{description}

This is one gate-sized branch in the filed roadmap. Do not expand scope to the rest of {vid}.

## Sources

{source_lines}

## Required behavior

- Inspect existing implementation before adding a parallel subsystem.
- Prefer the cheapest capable local/DeepSeek worker; summon frontier judgment only for uncertainty.
- Preserve T0/T1 locally and keep external seats optional.
- Add or update focused tests for the gate.
- Run the full repository test suite.
- File `{evidence_path.relative_to(ROOT).as_posix()}` with commands, results, changed paths, costs if available, and unresolved risks.
- Record the release gate only after evidence is green; do not mark the release shipped automatically.
{verify_lines}

## Done when

1. Focused tests for `{gid}` pass.
2. Full `pytest tests -q` passes.
3. The evidence JSON exists and identifies `{vid}`, `{gid}`, test totals, and the commit/branch.
4. `release record {vid} {gid}` is filed with the evidence path.

## Stop conditions

Stop only for a genuine external dependency, secret, spending/publishing approval, irreversible action, or failed evidence that cannot be repaired safely.
"""
    cfg = {
        "schema": "coding_session_loop.v1",
        "session_id": f"roadmap-{slug}",
        "commitment": selection.get("commitment") or f"roadmap-{vid}",
        "goal": goal,
        "playbook": "code_scout_janitor",
        "surface": "roadmap",
        "loop_mode": "loop",
        "gates": {
            "preflight": [
                {"id": "frozen_build", "cmd": f'python -c "from mag.factory_gate import check_frozen_build; assert check_frozen_build({goal!r}).get(\'ok\')"'},
            ],
            "session_done": [
                {"id": "roadmap_evidence", "path": evidence_path.relative_to(ROOT).as_posix()},
                {"id": "full_tests", "cmd": "python -m pytest tests -q"},
            ],
        },
        "scrum": {
            "sprint_0_preflight": {"owner": "router", "done_when": "frozen BUILD gate passes"},
            "sprint_1_implement": {"owner": "deepseek+local", "desk_task": goal, "artifact": evidence_path.relative_to(ROOT).as_posix()},
            "sprint_2_verify": {"owner": "verifier", "done_when": "full tests green and evidence filed"},
        },
        "knowns": [f"Roadmap selected {vid}.{gid}", f"Frozen contract: queue/handoff/{build_path.name}", *sources],
        "unknowns": ["Implementation delta and external blockers must be discovered from the repository and source docs."],
        "current_sprint": "sprint_0_preflight",
        "done_marker": "Done",
        "bead_on_close": True,
        "clear_dialogue_on_seed": True,
        "roadmap": {"version": vid, "gate": gid, "evidence_path": evidence_path.relative_to(ROOT).as_posix()},
    }
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    RUN_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    build_path.write_text(build, encoding="utf-8")
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return {
        "ok": True,
        "schema": "roadmap_run_contract.v1",
        "selection": selection,
        "goal": goal,
        "build_path": str(build_path.relative_to(ROOT)).replace("\\", "/"),
        "config_path": str(config_path.relative_to(ROOT)).replace("\\", "/"),
        "evidence_path": str(evidence_path.relative_to(ROOT)).replace("\\", "/"),
        "branch_prefix": f"mag/roadmap-{slug}",
    }


def run_next(*, version: str | None = None, gate: str | None = None, prepare_only: bool = False, dry: bool = False, max_ticks: int = 50) -> dict[str, Any]:
    selection = select_next(version=version, gate=gate)
    contract = compile_run(selection)
    if not contract.get("ok") or prepare_only:
        return contract
    from mag.factory_machine import factory_machine_run

    result = factory_machine_run(
        config_path=ROOT / contract["config_path"],
        branch_prefix=contract["branch_prefix"],
        note=contract["goal"],
        max_ticks=max_ticks,
        dry=dry,
        force_new_seed=True,
    )
    return {"ok": result.get("ok") is not False, "schema": "roadmap_run.v1", "contract": contract, "machine": result}


def status() -> dict[str, Any]:
    return {"ok": True, "schema": "roadmap_runner_status.v1", "next": select_next()}
