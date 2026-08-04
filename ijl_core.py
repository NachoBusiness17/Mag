"""Internal Judge Loop helpers — PlanSearch-lite, process value, skill beads.

Pure contracts stolen from open P0 papers (SECToR / PlanSearch / GCRM).
No SSI architecture. Local files only.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import MEMORY_DIR, ROOT

SKILLS_DIR = MEMORY_DIR / "improve" / "pins" / "skills"
SCHEMA = "mag_skill_bead.v1"


def slugify(text: str, *, max_len: int = 48) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return (s or "skill")[:max_len]


def infer_task_family(goal: str) -> str:
    g = (goal or "").lower()
    if any(k in g for k in ("dig", "research", "arxiv", "paper", "ssi", "ilya")):
        return "dig"
    if any(k in g for k in ("mirror", "chord", "presented", "nacho")):
        return "mirror"
    if any(k in g for k in ("mag", "harness", "context-pack", "trail", "seat")):
        return "harness"
    if any(k in g for k in ("code", "refactor", "test", "pytest", "implement")):
        return "code"
    return "general"


def _tokens(step: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", (step or "").lower()) if len(t) > 2}


def plan_signature(plan: list[str]) -> set[str]:
    sig: set[str] = set()
    for step in plan or []:
        sig |= _tokens(step)
    return sig


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def plan_pair_diversity(p1: list[str], p2: list[str]) -> float:
    """1 - Jaccard on step tokens; higher = more diverse."""
    return 1.0 - jaccard(plan_signature(p1), plan_signature(p2))


def mean_pairwise_diversity(plans: list[list[str]]) -> float:
    if len(plans) < 2:
        return 0.0
    scores: list[float] = []
    for i in range(len(plans)):
        for j in range(i + 1, len(plans)):
            scores.append(plan_pair_diversity(plans[i], plans[j]))
    return sum(scores) / len(scores) if scores else 0.0


def pick_primary_plan_index(plans: list[list[str]]) -> int:
    """Prefer a plan that is most different from the others (centroid diversity)."""
    if not plans:
        return 0
    if len(plans) == 1:
        return 0
    best_i = 0
    best_score = -1.0
    for i, p in enumerate(plans):
        others = [plans[j] for j in range(len(plans)) if j != i]
        score = sum(plan_pair_diversity(p, o) for o in others) / len(others)
        # slight preference for shorter plans (token economy)
        score += max(0.0, 0.05 * (8 - len(p)))
        if score > best_score:
            best_score = score
            best_i = i
    return best_i


def normalize_plans(raw: Any, *, max_plans: int = 3, max_steps: int = 6) -> list[list[str]]:
    """Accept plans as list[list] or single plan list; drop empties/dupes."""
    plans: list[list[str]] = []
    if not raw:
        return plans
    if isinstance(raw, list) and raw and isinstance(raw[0], str):
        # single plan
        steps = [str(x).strip() for x in raw if str(x).strip()][:max_steps]
        return [steps] if steps else []
    if isinstance(raw, list):
        for item in raw[:max_plans]:
            if isinstance(item, list):
                steps = [str(x).strip() for x in item if str(x).strip()][:max_steps]
                if steps:
                    plans.append(steps)
            elif isinstance(item, dict) and item.get("steps"):
                steps = [str(x).strip() for x in item["steps"] if str(x).strip()][:max_steps]
                if steps:
                    plans.append(steps)
    # dedupe by signature
    seen: list[set[str]] = []
    unique: list[list[str]] = []
    for p in plans:
        sig = plan_signature(p)
        if any(jaccard(sig, s) > 0.92 for s in seen):
            continue
        seen.append(sig)
        unique.append(p)
    return unique[:max_plans]


def normalize_value(data: dict[str, Any] | None) -> dict[str, Any]:
    d = data if isinstance(data, dict) else {}
    valence = str(d.get("valence") or "mixed").lower()
    if valence not in {"good", "mixed", "bad"}:
        valence = "mixed"
    try:
        intensity = float(d.get("intensity") if d.get("intensity") is not None else 0.5)
    except (TypeError, ValueError):
        intensity = 0.5
    intensity = max(0.0, min(1.0, intensity))
    next_act = str(d.get("next") or "continue").lower()
    if next_act not in {"continue", "revise", "abort", "escalate"}:
        next_act = "continue"
    flags = d.get("capture_flags") or []
    if not isinstance(flags, list):
        flags = [str(flags)]
    return {
        "valence": valence,
        "intensity": intensity,
        "stuck": bool(d.get("stuck")),
        "capture_flags": [str(x) for x in flags][:8],
        "tier_ok": bool(d.get("tier_ok", True)),
        "short_circuit": bool(d.get("short_circuit")),
        "reason": str(d.get("reason") or "")[:400],
        "next": next_act,
    }


def map_value_to_decision(
    value: dict[str, Any],
    *,
    base_decision: str,
    step_i: int,
    plan_len: int,
    retries: int,
    has_tool_ok: bool,
) -> str:
    """Merge process value with critic decision. Never free-escalate."""
    decision = (base_decision or "done").lower()
    if decision not in {"continue", "replan", "done", "escalate", "wait"}:
        decision = "done"

    v = normalize_value(value)
    if not v.get("tier_ok"):
        return "wait"
    if v.get("next") == "escalate" or decision == "escalate":
        # caller must re-check priority tags
        return "escalate"
    if v.get("short_circuit") or v.get("next") in {"revise", "abort"} or v.get("stuck"):
        if v.get("valence") == "bad" or v.get("short_circuit") or v.get("stuck"):
            return "replan"
    if v.get("valence") == "bad" and v.get("intensity", 0) >= 0.6:
        return "replan"

    if decision == "continue" and step_i >= max(plan_len, 1) and retries >= 1:
        return "done" if has_tool_ok else "replan"
    return decision


def write_skill_bead(
    *,
    goal: str,
    plan: list[str],
    success_checks: list[str],
    critique: str,
    value_trace: list[dict[str, Any]] | None = None,
    tool_ok_count: int = 0,
    task_family: str | None = None,
    parent_run: str | None = None,
) -> Path | None:
    """FILE a skill bead after a successful run. Returns path or None if skip."""
    if tool_ok_count < 1 and not (plan and critique):
        return None
    family = task_family or infer_task_family(goal)
    slug = slugify(f"{family}-{goal}")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    commitment = f"skill-{slug}-001"
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = SKILLS_DIR / f"{slug}.md"
    # append version suffix if exists with different goal
    if path.is_file():
        path = SKILLS_DIR / f"{slug}-{ts}.md"

    mid = []
    for v in (value_trace or [])[-6:]:
        if isinstance(v, dict):
            mid.append(
                f"- valence={v.get('valence')} short={v.get('short_circuit')} "
                f"next={v.get('next')}: {v.get('reason', '')[:120]}"
            )
    body = f"""# skill: {slug}

**commitment:** `{commitment}`  
**schema:** {SCHEMA}  
**task_family:** {family}  
**parent_run:** {parent_run or ""}  
**ts:** {ts}

## When to load
Goal keywords match this family or similar: {goal[:200]}

## Steps that worked
{chr(10).join(f"- {s}" for s in (plan or [])[:8]) or "- (none recorded)"}

## Success checks
{chr(10).join(f"- {c}" for c in (success_checks or [])[:8]) or "- (none)"}

## Critique (distill)
{(critique or "")[:800]}

## Value mid-signals that saved compute
{chr(10).join(mid) or "- (none)"}

## Antiskill
Do not re-run thrash paths that short-circuited with valence=bad.

## Tool ok count
{tool_ok_count}
"""
    path.write_text(body, encoding="utf-8")
    meta = {
        "schema": SCHEMA,
        "slug": slug,
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "task_family": family,
        "goal": goal[:300],
        "ts": ts,
        "commitment": commitment,
    }
    meta_path = path.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path


def list_skill_beads(*, task_family: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
    if not SKILLS_DIR.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for p in sorted(SKILLS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            o = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if task_family and str(o.get("task_family") or "") != task_family:
            continue
        items.append(o)
        if len(items) >= limit:
            break
    return items


def skill_excerpt_for_goal(goal: str, *, max_chars: int = 700) -> str:
    """LOAD top skill beads matching task family / keywords."""
    family = infer_task_family(goal)
    beads = list_skill_beads(task_family=family, limit=4)
    if not beads:
        beads = list_skill_beads(limit=3)
    if not beads:
        return ""
    gtoks = _tokens(goal)
    scored: list[tuple[float, dict[str, Any]]] = []
    for b in beads:
        btoks = _tokens(str(b.get("goal") or "") + " " + str(b.get("slug") or ""))
        scored.append((jaccard(gtoks, btoks), b))
    scored.sort(key=lambda x: x[0], reverse=True)
    chunks: list[str] = [f"task_family_hint: {family}"]
    budget = max_chars
    for score, b in scored[:3]:
        rel = b.get("path") or ""
        path = ROOT / rel if rel and not Path(rel).is_absolute() else Path(rel) if rel else None
        body = ""
        if path and path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                # take When + Steps
                lines = []
                for ln in text.splitlines():
                    if ln.startswith("## Antiskill"):
                        break
                    lines.append(ln)
                body = "\n".join(lines)[: min(280, budget)]
            except OSError:
                body = str(b.get("goal") or "")[:120]
        else:
            body = str(b.get("goal") or "")[:120]
        block = f"### skill {b.get('slug')} (sim={score:.2f})\n{body}"
        chunks.append(block)
        budget -= len(block)
        if budget < 80:
            break
    return "\n\n".join(chunks)[:max_chars]


def next_alt_plan(
    alt_plans: list[list[str]] | None,
    plan_index: int,
) -> tuple[list[str] | None, int]:
    """Advance to next alternative plan if any. Returns (plan, new_index) or (None, index)."""
    alts = alt_plans or []
    nxt = int(plan_index) + 1
    if 0 <= nxt < len(alts):
        return list(alts[nxt]), nxt
    return None, int(plan_index)
