"""Ponytail ladder audit — over-engineering scan (Mag v2).

Ref: https://github.com/dietrichgebert/ponytail
Law: ladder cuts code bloat; tiers/gates/residual never cut.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from config import ROOT

SCHEMA = "ponytail_audit.v1"

SKIP_DIRS = {
    ".git", ".venv", "node_modules", "__pycache__", "dist", "build",
    ".pytest_cache", "memory", "logs", "state", "derived",
}

KNOWN_DUP_CONSTS = (("DEPTH_JOB_MAP", ("mag/router.py", "mag/governor_autorun.py")),)

ABANDONED_MARKERS = (
    ("sovereign-mirror-scaffold", "mag/lattice_loop.py", "external dep — optional spore only"),
)

SHRINK_THRESHOLD_LINES = 900


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _iter_py() -> list[Path]:
    out: list[Path] = []
    for p in ROOT.rglob("*.py"):
        if set(p.parts) & SKIP_DIRS:
            continue
        r = _rel(p)
        if r.startswith("tests/"):
            continue
        out.append(p)
    return sorted(out)


def _find_duplicate_constants() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for name, paths in KNOWN_DUP_CONSTS:
        present = [p for p in paths if (ROOT / p).is_file()]
        defs = []
        for rel in present:
            text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            if re.search(rf"^{name}\s*:", text, re.M):
                defs.append(rel)
        if len(defs) > 1:
            findings.append(
                {
                    "tag": "dup",
                    "what": f"{name} defined in multiple modules",
                    "replacement": "import from mag.router only",
                    "paths": defs,
                    "severity": "high",
                }
            )
        elif len(defs) == 1 and len(present) > 1:
            importers = [p for p in present if p not in defs]
            if importers:
                findings.append(
                    {
                        "tag": "dup",
                        "what": f"{name} — verify single definition",
                        "replacement": "import from mag.router",
                        "paths": present,
                        "severity": "low",
                    }
                )
    return findings


def _scan_large_files(files: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in files:
        try:
            n = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            continue
        if n >= SHRINK_THRESHOLD_LINES:
            out.append(
                {
                    "tag": "shrink",
                    "what": f"{n} lines",
                    "replacement": "split only when phase demands",
                    "path": _rel(p),
                    "severity": "low",
                }
            )
    return out


def _scan_yagni_wrappers(files: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in files:
        if not _rel(p).startswith("mag/"):
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or len(node.body) != 1:
                continue
            body = node.body[0]
            if isinstance(body, ast.Return) and isinstance(body.value, ast.Call):
                if len(node.args.args) > 3:
                    continue
                out.append(
                    {
                        "tag": "yagni",
                        "what": f"wrapper `{node.name}`",
                        "replacement": "inline or delete",
                        "path": f"{_rel(p)}:{node.lineno}",
                        "severity": "low",
                    }
                )
    return out[:12]


def _scan_abandoned() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for needle, path, note in ABANDONED_MARKERS:
        fp = ROOT / path
        if fp.is_file() and needle in fp.read_text(encoding="utf-8", errors="replace"):
            out.append(
                {"tag": "delete", "what": needle, "replacement": note, "path": path, "severity": "low"}
            )
    return out


def _ladder_compliance() -> dict[str, Any]:
    required = [
        "mag/router.py", "mag/failure_kb.py", "mag/verkle_audit.py",
        "docs/ref/MAG_v2_PLAN.md", "docs/ref/lessig_1_6.md", "configs/modules.yaml",
    ]
    missing = [p for p in required if not (ROOT / p).is_file()]
    return {"ok": not missing, "missing": missing}


def run_audit(*, hints: bool = False) -> dict[str, Any]:
    files = _iter_py()
    findings: list[dict[str, Any]] = []
    findings.extend(_find_duplicate_constants())
    findings.extend(_scan_abandoned())
    findings.extend(_scan_large_files(files))
    if hints:
        findings.extend(_scan_yagni_wrappers(files))

    sev_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: (sev_order.get(f.get("severity", "low"), 9), f.get("tag", "")))
    lean = not any(f.get("severity") in ("high", "medium") for f in findings)

    return {
        "ok": True,
        "schema": SCHEMA,
        "lean": lean,
        "summary": "Lean already. Ship." if lean else f"{len(findings)} finding(s).",
        "files_scanned": len(files),
        "findings": findings,
        "ladder_compliance": _ladder_compliance(),
        "ponytail": "https://github.com/dietrichgebert/ponytail",
    }


def format_report(res: dict[str, Any]) -> str:
    if res.get("lean"):
        return str(res.get("summary"))
    lines = [str(res.get("summary")), ""]
    for f in res.get("findings") or []:
        path = f.get("path") or ",".join(f.get("paths") or [])
        lines.append(f"{f.get('tag')}: {f.get('what')}. {f.get('replacement')} [{path}]")
    lines.append(f"\nScanned {res.get('files_scanned', 0)} files.")
    return "\n".join(lines)
