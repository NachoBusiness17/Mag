"""Failure Knowledge Base (FKB) — searchable store of failures, fixes, and recurrence.

Captures tool failures and collapse signatures, deduplicates by signature, auto-drafts
remedy cards when a pattern recurs, and injects relevant hits into context packs.

Storage:
  logs/failure_kb.jsonl       — append-only event log
  memory/failure_kb/signatures.json — deduped index (count, last_seen, remedy_id)

Wire points:
  operator_inbox.log_behavioral_event → log_failure
  decision_framework.surface_tips → surface_hits
  agent_cli collapse / tool_fail → lookup + format_block
  improve._behavioral_candidates → recurring_patterns
  main.py fkb search|list|stats
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT

LOG_PATH = ROOT / "logs" / "failure_kb.jsonl"
INDEX_PATH = ROOT / "memory" / "failure_kb" / "signatures.json"
REMEDY_DIR = ROOT / "memory" / "remedies"
AUTO_DRAFT_THRESHOLD = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:max_len] or "unknown").strip("-")


def _normalize_error(error: str | None, detail: str | None) -> str:
    """Collapse noisy error text into a stable signature fragment."""
    blob = f"{error or ''} {detail or ''}".lower()
    blob = re.sub(r"\s+", " ", blob).strip()
    # Strip volatile paths / timestamps
    blob = re.sub(r"[a-f0-9]{8,}", "<hex>", blob)
    blob = re.sub(r"\d{4}-\d{2}-\d{2}[t\s]\d{2}:\d{2}:\d{2}", "<ts>", blob)
    return blob[:240]


def signature_key(*, tool: str | None = None, error: str | None = None, detail: str | None = None) -> str:
    tool_s = (tool or "").strip().lower() or "_"
    norm = _normalize_error(error, detail)
    digest = hashlib.sha256(f"{tool_s}|{norm}".encode()).hexdigest()[:12]
    return f"{tool_s}:{digest}"


def _load_index() -> dict[str, Any]:
    if not INDEX_PATH.is_file():
        return {"schema": "failure_kb.signatures.v1", "signatures": {}}
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("signatures"), dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"schema": "failure_kb.signatures.v1", "signatures": {}}


def _save_index(data: dict[str, Any]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def log_failure(
    *,
    kind: str,
    detail: str = "",
    tool: str | None = None,
    error: str | None = None,
    phase: str | None = None,
    session_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Record a failure event; bump signature count; maybe auto-draft remedy."""
    sig = signature_key(tool=tool, error=error, detail=detail)
    row = {
        "ts": _now(),
        "kind": kind,
        "sig": sig,
        "detail": (detail or "")[:500],
        "tool": tool,
        "error": (error or "")[:300] if error else None,
        "phase": phase,
        "session_id": session_id,
        "provider": provider,
        "model": model,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass

    idx = _load_index()
    sigs: dict[str, Any] = idx.setdefault("signatures", {})
    rec = sigs.get(sig) or {
        "sig": sig,
        "tool": tool,
        "error_sample": (error or "")[:200],
        "detail_sample": (detail or "")[:200],
        "kind": kind,
        "count": 0,
        "first_seen": row["ts"],
        "last_seen": row["ts"],
        "remedy_id": None,
    }
    rec["count"] = int(rec.get("count") or 0) + 1
    rec["last_seen"] = row["ts"]
    rec["kind"] = kind
    if tool:
        rec["tool"] = tool
    if error:
        rec["error_sample"] = error[:200]
    if detail:
        rec["detail_sample"] = detail[:200]
    sigs[sig] = rec
    _save_index(idx)

    drafted = None
    if int(rec["count"]) >= AUTO_DRAFT_THRESHOLD and not rec.get("remedy_id"):
        drafted = auto_draft_remedy(rec)
        if drafted:
            rec["remedy_id"] = drafted
            sigs[sig] = rec
            _save_index(idx)

    return {"ok": True, "sig": sig, "count": rec["count"], "remedy_id": rec.get("remedy_id"), "drafted": drafted}


def auto_draft_remedy(rec: dict[str, Any]) -> str | None:
    """When a signature recurs, draft a remedy card if none exists."""
    tool = str(rec.get("tool") or "unknown")
    sig = str(rec.get("sig") or "")
    count = int(rec.get("count") or 0)
    if count < AUTO_DRAFT_THRESHOLD:
        return None

    try:
        from mag import remedy

        existing = remedy.by_tool(tool)
        if existing:
            return str(existing.get("id") or existing.get("name") or "")
    except Exception:
        pass

    REMEDY_DIR.mkdir(parents=True, exist_ok=True)
    rid = f"rem-auto-{_slug(tool)}-{_slug(sig.split(':')[-1] if ':' in sig else sig, 16)}"
    path = REMEDY_DIR / f"{rid}.md"
    if path.is_file():
        return rid

    err = str(rec.get("error_sample") or "")
    det = str(rec.get("detail_sample") or "")
    sig_re = re.escape(_normalize_error(err, det)[:80]) if (err or det) else tool
    body = f"""id: {rid}
name: auto {tool} failure (×{count})
tools: {tool}
signature: {sig_re}

## Prevent
This failure signature recurred {count} times in Mag runs ({sig}).
Tool: `{tool}`. Error: {err or '(see detail)'}.

## Fix
1. Read the target file/area first (`read_file` with line range).
2. Emit flat tool args — sibling keys, not nested `arguments`/`parameters` blobs.
3. One surgical `write_file` (search+replace) or one create-with-content — then verify.
4. If stuck: `python main.py fkb lookup "{tool}"` or `!remedy {tool}`.

## Probe
```text
python main.py fkb stats
```
"""
    try:
        path.write_text(body, encoding="utf-8")
    except OSError:
        return None
    return rid


def _read_log(*, tail: int = 200) -> list[dict[str, Any]]:
    if not LOG_PATH.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines[-tail:]:
        if not line.strip():
            continue
        try:
            o = json.loads(line)
            if isinstance(o, dict):
                rows.append(o)
        except json.JSONDecodeError:
            continue
    return rows


def query(text: str = "", *, tool: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """Search deduped signatures by tool name or free-text (error/detail)."""
    q = (text or "").strip().lower()
    idx = _load_index()
    sigs: list[dict[str, Any]] = list((idx.get("signatures") or {}).values())
    hits: list[tuple[int, dict[str, Any]]] = []
    for rec in sigs:
        if tool and str(rec.get("tool") or "").lower() != tool.lower():
            continue
        hay = " ".join(
            [
                str(rec.get("tool") or ""),
                str(rec.get("error_sample") or ""),
                str(rec.get("detail_sample") or ""),
                str(rec.get("sig") or ""),
            ]
        ).lower()
        if q and q not in hay:
            continue
        score = int(rec.get("count") or 0)
        hits.append((score, rec))
    hits.sort(key=lambda x: (-x[0], str(x[1].get("last_seen") or "")), reverse=False)
    return [r for _, r in hits[:limit]]


def lookup(tool: str | None = None, error_text: str = "", *, limit: int = 3) -> list[dict[str, Any]]:
    """Agent-friendly lookup: tool + optional error substring."""
    return query(error_text, tool=tool, limit=limit)


def surface_hits(*, goal: str = "", tool: str | None = None, limit: int = 4) -> list[dict[str, str]]:
    """Tips-shaped hits for context_pack / decision_framework."""
    g = (goal or "").lower()
    # Goal keywords boost relevant tools
    tool_hint = tool
    if not tool_hint:
        for t in ("write_file", "run_python", "run_shell", "read_file"):
            if t.replace("_", " ") in g or t in g:
                tool_hint = t
                break
    hits = query(g[:80], tool=tool_hint, limit=limit)
    if not hits and g:
        hits = query(g[:80], limit=limit)
    out: list[dict[str, str]] = []
    for rec in hits:
        cnt = int(rec.get("count") or 0)
        if cnt < 2:
            continue
        tool_s = str(rec.get("tool") or "?")
        det = str(rec.get("detail_sample") or rec.get("error_sample") or "")[:120]
        rid = str(rec.get("remedy_id") or "")
        tip = f"FKB ×{cnt}: {tool_s} — {det}" if det else f"FKB ×{cnt}: {tool_s} failure pattern"
        avoid = f"remedy={rid}" if rid else "check memory/remedies/"
        out.append({"id": f"fkb-{rec.get('sig', '')[:16]}", "tip": tip, "avoid": avoid, "source": "failure_kb"})
    return out


def format_block(hits: list[dict[str, Any]] | list[dict[str, str]], *, max_chars: int = 700) -> str:
    if not hits:
        return ""
    lines = ["[FAILURE KB — recurring patterns (do not repeat)]"]
    for h in hits[:5]:
        if "tip" in h:
            lines.append(f"- {h.get('tip', '')}")
            if h.get("avoid"):
                lines.append(f"  → {h['avoid'][:120]}")
        else:
            cnt = int(h.get("count") or 0)
            tool_s = h.get("tool") or "?"
            det = (h.get("detail_sample") or h.get("error_sample") or "")[:100]
            lines.append(f"- ×{cnt} {tool_s}: {det}")
            if h.get("remedy_id"):
                lines.append(f"  → remedy: {h['remedy_id']}")
    block = "\n".join(lines)
    return block[:max_chars]


def recurring_patterns(*, min_count: int = 3) -> list[dict[str, Any]]:
    """Patterns for improve scout / risk candidates."""
    idx = _load_index()
    out = []
    for rec in (idx.get("signatures") or {}).values():
        if int(rec.get("count") or 0) >= min_count:
            out.append(rec)
    out.sort(key=lambda r: (-int(r.get("count") or 0), str(r.get("last_seen") or "")))
    return out


def stats() -> dict[str, Any]:
    idx = _load_index()
    sigs = list((idx.get("signatures") or {}).values())
    events = len(_read_log(tail=10000))
    return {
        "ok": True,
        "events_logged": events,
        "signatures": len(sigs),
        "recurring": len([s for s in sigs if int(s.get("count") or 0) >= AUTO_DRAFT_THRESHOLD]),
        "with_remedy": len([s for s in sigs if s.get("remedy_id")]),
        "log_path": str(LOG_PATH),
        "index_path": str(INDEX_PATH),
    }


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] in ("stats", "status"):
        print(json.dumps(stats(), indent=2))
        return 0
    if argv[0] == "list":
        rows = query("", limit=int(argv[1]) if len(argv) > 1 else 20)
        print(json.dumps(rows, indent=2, default=str)[:12000])
        return 0
    if argv[0] in ("search", "lookup", "query"):
        q = " ".join(argv[1:]) if len(argv) > 1 else ""
        tool = None
        if q.startswith("tool:"):
            parts = q.split(None, 1)
            tool = parts[0].split(":", 1)[1]
            q = parts[1] if len(parts) > 1 else ""
        rows = query(q, tool=tool, limit=10)
        print(format_block(rows) or json.dumps(rows, indent=2, default=str))
        return 0 if rows else 1
    if argv[0] == "record" and len(argv) >= 2:
        # record tool_fail write_file "detail" --error preflight
        kind = argv[1]
        tool = argv[2] if len(argv) > 2 else None
        detail = argv[3] if len(argv) > 3 else ""
        error = None
        for i, a in enumerate(argv):
            if a == "--error" and i + 1 < len(argv):
                error = argv[i + 1]
        r = log_failure(kind=kind, tool=tool, detail=detail, error=error)
        print(json.dumps(r, indent=2))
        return 0
    print(
        "usage: python -m mag.failure_kb [stats|list|search <q>|record <kind> <tool> <detail> [--error E]]"
    )
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
