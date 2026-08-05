"""Release registry — version gates + behavioral memory (release_milestone).

Machine truth: configs/releases.yaml
Operator gate log: memory/improve/releases/gates.jsonl
Training events: memory/training/events.jsonl (pattern release_milestone)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from config import CONFIGS_DIR, ROOT

REGISTRY_PATH = CONFIGS_DIR / "releases.yaml"
GATES_LOG = ROOT / "memory" / "improve" / "releases" / "gates.jsonl"
RELEASES_DIR = ROOT / "docs" / "ref" / "releases"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        return {"schema": "mag_releases.v1", "releases": []}
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    data.setdefault("releases", [])
    return data


def get_release(version_id: str) -> dict[str, Any] | None:
    vid = (version_id or "").strip().lstrip("v")
    if not vid:
        return None
    for rel in load_registry().get("releases") or []:
        rid = str(rel.get("id") or "").lstrip("v")
        if rid == vid:
            return rel
    return None


def list_releases() -> list[dict[str, Any]]:
    return list(load_registry().get("releases") or [])


def notes_path(version_id: str) -> Path | None:
    rel = get_release(version_id)
    if not rel:
        return None
    p = rel.get("notes_path")
    return (ROOT / p) if p else None


def status_summary() -> dict[str, Any]:
    rows = []
    for rel in list_releases():
        vid = rel.get("id")
        gates = rel.get("gates") or []
        rows.append({
            "id": vid,
            "status": rel.get("status"),
            "notes_path": rel.get("notes_path"),
            "gates_defined": len(gates),
            "gate_ids": [g.get("id") for g in gates if isinstance(g, dict)],
        })
    return {"ok": True, "releases": rows, "registry": str(REGISTRY_PATH)}


def _append_gate_log(row: dict[str, Any]) -> None:
    GATES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with GATES_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def read_gate_log(*, limit: int = 50, version: str | None = None) -> list[dict[str, Any]]:
    if not GATES_LOG.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in GATES_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(o, dict):
            continue
        if version and str(o.get("version", "")).lstrip("v") != version.lstrip("v"):
            continue
        out.append(o)
    return out[-limit:]


def record_gate(
    version: str,
    gate_id: str,
    *,
    ok: bool = True,
    note: str = "",
    evidence_path: str = "",
) -> dict[str, Any]:
    """Record a version graduation gate — FILE to gates.jsonl + training event."""
    rel = get_release(version)
    if not rel:
        return {"ok": False, "error": f"unknown version {version!r}"}
    vid = str(rel.get("id") or version)
    gid = (gate_id or "").strip()
    if not gid:
        return {"ok": False, "error": "gate_id required"}

    row = {
        "schema": "mag_release_gate.v1",
        "ts": _now(),
        "version": vid,
        "gate_id": gid,
        "ok": bool(ok),
        "note": (note or "")[:2000],
        "evidence_path": (evidence_path or "")[:500],
        "commitment": rel.get("commitment"),
    }
    _append_gate_log(row)

    gates_rel = str(GATES_LOG)
    try:
        gates_rel = str(GATES_LOG.relative_to(ROOT))
    except ValueError:
        pass

    try:
        from mag.training_events import emit

        emit(
            "release_milestone",
            join={"version": vid, "gate_id": gid},
            input_data={"version": vid, "gate_id": gid, "note": note[:500]},
            action={"kind": "gate_record", "ok": ok},
            outcome={"filed": True, "gates_log": gates_rel},
            pattern_tags=["release", vid, gid],
            tier_max="T2",
            exportable=True,
        )
    except Exception:
        pass

    return {"ok": True, "recorded": row}


def format_notes_text(version_id: str) -> str:
    p = notes_path(version_id)
    if not p or not p.is_file():
        return f"(no release notes at registry path for {version_id})"
    return p.read_text(encoding="utf-8", errors="replace")
