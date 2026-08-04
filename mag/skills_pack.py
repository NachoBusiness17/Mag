"""Progressive skill excerpts for context-pack (skills > MCP flood)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config import CONFIGS_DIR, ROOT

CFG = CONFIGS_DIR / "skills.yaml"


def load_skills_cfg() -> dict[str, Any]:
    if not CFG.is_file():
        return {}
    return yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}


def _resolve_path(rel: str) -> Path | None:
    if not rel:
        return None
    if rel.startswith("~/") or rel.startswith("~\\"):
        p = Path.home() / rel[2:]
    else:
        p = ROOT / rel
    return p if p.is_file() else None


def _clip_file(path: Path, n: int = 400) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    # first meaningful lines
    lines = []
    for ln in text.splitlines():
        if ln.strip().startswith("#") or ln.strip().startswith("**") or ln.strip():
            lines.append(ln)
        if sum(len(x) for x in lines) > n:
            break
    out = "\n".join(lines)[:n]
    return out


def skills_for_job(job: str, *, max_chars: int = 800) -> str:
    cfg = load_skills_cfg()
    job_map = cfg.get("job_to_skills") or {}
    skill_ids = list(job_map.get(job) or job_map.get("default") or [])
    if not skill_ids:
        return ""
    by_id = {s.get("id"): s for s in (cfg.get("skills") or []) if isinstance(s, dict)}
    chunks: list[str] = []
    memory_rule = (cfg.get("memory_rule") or "").strip()
    if memory_rule:
        chunks.append("memory_rule: " + " ".join(memory_rule.split())[:200])
    budget = max_chars
    for sid in skill_ids:
        spec = by_id.get(sid) or {}
        if not spec.get("pack_excerpt", True):
            continue
        path = _resolve_path(str(spec.get("path") or ""))
        if not path:
            chunks.append(f"- {sid}: (path missing)")
            continue
        take = min(280, max(80, budget // max(1, len(skill_ids))))
        body = _clip_file(path, take)
        chunks.append(f"### {sid}\n{body}")
        budget -= len(body)
        if budget < 50:
            break
    text = "\n\n".join(chunks)
    return text[:max_chars]
