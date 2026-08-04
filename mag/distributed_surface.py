"""Distributed surface glue — multi-device viewport on home soil.

Commitment: distributed-surface-glue-001
Plan: docs/ref/DISTRIBUTED_SURFACE.md
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT, bind_host

CONFIG_PATH = ROOT / "configs" / "distributed_surface.yaml"
DEFAULT_INBOUND = ROOT / "memory" / "handoff" / "inbound"


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        import yaml  # type: ignore

        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def phase() -> str:
    return str(_load_yaml().get("phase") or "G0")


def inbound_dir() -> Path:
    cfg = _load_yaml()
    rel = ((cfg.get("handoff") or {}).get("inbound_dir") or "memory/handoff/inbound")
    return ROOT / rel


def max_handoff_chars() -> int:
    cfg = _load_yaml()
    try:
        return int((cfg.get("handoff") or {}).get("max_chars") or 24000)
    except (TypeError, ValueError):
        return 24000


def _slug(s: str, n: int = 32) -> str:
    out = re.sub(r"[^a-zA-Z0-9]+", "-", (s or "device").strip().lower()).strip("-")
    return (out[:n] or "device").rstrip("-")


def ingest_file_block(
    text: str,
    *,
    source: str = "unknown",
    device: str = "unknown",
) -> dict[str, Any]:
    """Append a FILE block or goal note to memory/handoff/inbound/."""
    body = (text or "").strip()
    if not body:
        return {"ok": False, "error": "empty text"}
    if len(body) > max_handoff_chars():
        return {"ok": False, "error": f"text exceeds {max_handoff_chars()} chars"}

    dest = inbound_dir()
    dest.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"{ts}_{_slug(source)}_{_slug(device)}.md"
    path = dest / fname
    header = (
        f"<!-- mag handoff inbound · {ts} · source={source} · device={device} -->\n\n"
    )
    path.write_text(header + body + "\n", encoding="utf-8")

    # Pointer for context-pack / operator glance
    latest = ROOT / "memory" / "handoff" / "latest_inbound.md"
    try:
        latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        pass

    return {
        "ok": True,
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": len(body),
        "source": source,
        "device": device,
    }


def list_inbound(limit: int = 10) -> list[dict[str, Any]]:
    d = inbound_dir()
    if not d.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for p in sorted(d.glob("*.md"), reverse=True)[: max(1, limit)]:
        try:
            st = p.stat()
            rows.append(
                {
                    "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": st.st_size,
                    "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                }
            )
        except OSError:
            continue
    return rows


def surface_status() -> dict[str, Any]:
    """Status for GET /api/v1/surface — plan phase + reach hints."""
    import os

    cfg = _load_yaml()
    remote = cfg.get("remote") or {}
    port = int(remote.get("port") or 8765)
    host = bind_host(str(remote.get("bind_host") or "127.0.0.1"))
    public = (os.environ.get("MAG_PUBLIC_URL") or remote.get("public_url") or "").strip()
    inbound = list_inbound(limit=3)
    return {
        "ok": True,
        "commitment": "distributed-surface-glue-001",
        "phase": phase(),
        "plan": "docs/ref/DISTRIBUTED_SURFACE.md",
        "runbook": "memory/handoff/HOME_MACHINE.md",
        "bind": {"host": host, "port": port},
        "public_url": public or None,
        "inbound_dir": str(inbound_dir().relative_to(ROOT)).replace("\\", "/"),
        "inbound_count": len(list(inbound_dir().glob("*.md"))) if inbound_dir().is_dir() else 0,
        "recent_inbound": inbound,
        "auth": {
            "token_env": ((cfg.get("auth") or {}).get("token_env") or "MAG_REMOTE_TOKEN"),
            "required_on_remote_bind": bool((cfg.get("auth") or {}).get("require_token_on_remote_bind")),
        },
    }
