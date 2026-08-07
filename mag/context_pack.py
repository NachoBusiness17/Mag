"""Minimum-token pack for Grok (this TUI) — never full chat."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT

VALID_PACK_MODES = frozenset({"janitor", "route", "build", "audit", "plan", "full"})

# Layer budgets per mode — janitor default for ask/steward
MODE_CONFIG: dict[str, dict[str, Any]] = {
    "janitor": {
        "max_brief": 400,
        "max_bonds": 500,
        "max_live": 0,
        "max_chars": 1200,
        "default_job": "ask",
        "include_resonance": False,
        "include_trail": False,
        "include_skills": False,
        "include_ijl": False,
        "include_heat": False,
        "include_coordination": False,
        "include_mirror_clue": False,
        "compact_nervous": True,
    },
    "route": {
        "max_brief": 600,
        "max_bonds": 800,
        "max_live": 200,
        "max_chars": 1800,
        "default_job": "route",
        "include_resonance": True,
        "include_trail": False,
        "include_skills": True,
        "include_ijl": False,
        "include_heat": False,
        "include_coordination": True,
        "include_mirror_clue": False,
        "compact_nervous": True,
    },
    "build": {
        "max_brief": 900,
        "max_bonds": 1200,
        "max_live": 400,
        "max_chars": 5500,
        "default_job": "build",
        "include_resonance": True,
        "include_trail": True,
        "include_skills": True,
        "include_ijl": True,
        "include_heat": False,
        "include_coordination": True,
        "include_mirror_clue": False,
        "include_build": True,
        "include_scope": True,
        "compact_nervous": False,
    },
    "audit": {
        "max_brief": 600,
        "max_bonds": 600,
        "max_live": 200,
        "max_chars": 7500,
        "default_job": "audit",
        "include_resonance": False,
        "include_trail": True,
        "include_skills": True,
        "include_ijl": False,
        "include_heat": False,
        "include_coordination": True,
        "include_mirror_clue": False,
        "include_build": True,
        "compact_nervous": False,
    },
    "plan": {
        "max_brief": 1200,
        "max_bonds": 1600,
        "max_live": 600,
        "max_chars": 11000,
        "default_job": "plan",
        "include_resonance": True,
        "include_trail": False,
        "include_skills": True,
        "include_ijl": True,
        "include_heat": True,
        "include_coordination": True,
        "include_mirror_clue": True,
        "compact_nervous": False,
    },
    "full": {
        "max_brief": 1200,
        "max_bonds": 1600,
        "max_live": 800,
        "max_chars": 4500,
        "default_job": "default",
        "include_resonance": True,
        "include_trail": True,
        "include_skills": True,
        "include_ijl": True,
        "include_heat": True,
        "include_coordination": True,
        "include_mirror_clue": True,
        "compact_nervous": False,
    },
}


def _normalize_mode(mode: str | None) -> str:
    m = (mode or "full").strip().lower()
    return m if m in VALID_PACK_MODES else "full"


def _read_build_excerpt(path: str | Path | None, *, max_chars: int = 4000) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        p = ROOT / str(path)
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")[:max_chars]


def _latest_scope_card(*, slug: str = "") -> str:
    scope_dir = ROOT / "memory" / "steward" / "scope_cards"
    if not scope_dir.is_dir():
        return ""
    if slug:
        p = scope_dir / f"{slug}.md"
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")[:2500]
    cards = sorted(scope_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not cards:
        return ""
    return cards[0].read_text(encoding="utf-8", errors="replace")[:2500]


def _env_on(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _republic_root() -> Path:
    env = os.environ.get("MAG_REPUBLIC_ROOT", "").strip()
    if env:
        return Path(env)
    return ROOT.parent / "mycelial-republic"


def _mirror_voice_excerpt(goal: str, *, max_chars: int = 600) -> str:
    """Compact mirror voice rows from republic mirror_train.jsonl."""
    if not _env_on("MAG_INJECT_MIRROR_VOICE", default=False):
        return ""
    path = _republic_root() / "data" / "annotated" / "mirror_train.jsonl"
    if not path.is_file():
        return ""
    goal_tokens = {t for t in re.findall(r"[a-z0-9]+", goal.lower()) if len(t) > 2}
    priority_tags = {"sovereign_mirror", "refusal", "rope", "chord", "meta", "mycelial"}
    rows: list[tuple[int, dict[str, Any]]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        body = str(row.get("text") or row.get("response") or "").strip()
        if not body:
            continue
        tags = set(row.get("knot_tags") or row.get("tags") or [])
        signal = str(row.get("signal") or "").lower()
        product = str(row.get("product_dna") or "").lower()
        score = 0
        if signal == "high":
            score += 4
        elif signal == "medium":
            score += 2
        if tags & priority_tags:
            score += 3
        if "sovereign_mirror" in product or "verkle" in product:
            score += 2
        if goal_tokens:
            score += len(goal_tokens & set(re.findall(r"[a-z0-9]+", body.lower())))
        if score > 0:
            rows.append((score, row))
    if not rows:
        return ""
    rows.sort(key=lambda x: x[0], reverse=True)
    lines = ["[MIRROR VOICE — operator corpus excerpt (presented, not interpreted)]"]
    used = 0
    for _, row in rows[:3]:
        rid = row.get("id") or "?"
        body = str(row.get("text") or row.get("response") or "").strip()
        snippet = body[:220] + ("…" if len(body) > 220 else "")
        block = f"- {rid}: {snippet}"
        if used + len(block) + 1 > max_chars:
            break
        lines.append(block)
        used += len(block) + 1
    return "\n".join(lines)[:max_chars]


def _clue_chain_excerpt(*, max_chars: int = 500) -> str:
    """Latest decoded clue bead from memory/improve/pins/clues/."""
    if not _env_on("MAG_INJECT_CLUE_CHAIN", default=False):
        return ""
    clues_dir = ROOT / "memory" / "improve" / "pins" / "clues"
    if not clues_dir.is_dir():
        return ""
    beads = sorted(clues_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not beads:
        return ""
    body = beads[0].read_text(encoding="utf-8", errors="replace").strip()
    if not body:
        return ""
    header = f"[CLUE CHAIN — latest bead: {beads[0].name}]"
    return f"{header}\n{body[: max_chars - len(header) - 2]}"


def _clip(path: Path, n: int) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:n]


def build_context_pack(
    *,
    mode: str = "full",
    job: str | None = None,
    build_path: str | Path | None = None,
    scope_slug: str = "",
    goal: str = "",
    max_brief: int | None = None,
    max_live: int | None = None,
    max_bonds: int | None = None,
    refresh_bonds: bool = False,
) -> dict[str, Any]:
    cfg = MODE_CONFIG[_normalize_mode(mode)]
    mode = _normalize_mode(mode)
    job = (job or cfg.get("default_job") or "default").strip()
    max_brief = max_brief if max_brief is not None else int(cfg["max_brief"])
    max_live = max_live if max_live is not None else int(cfg["max_live"])
    max_bonds = max_bonds if max_bonds is not None else int(cfg["max_bonds"])
    from mag.health import sanity
    from mag.lanes import latest_brief_text
    from models.multi_smoke import last_smoke
    from models.registry import inventory

    s = sanity()
    brief = latest_brief_text()[:max_brief]
    live = _clip(ROOT / "memory" / "live_from_grok.md", max_live)
    att = _clip(ROOT / "memory" / "attention.md", 600)
    directives = _clip(ROOT / "memory" / "operator_directives.md", 2800)
    todo = _clip(ROOT / "queue" / "todo.md", 500)
    smoke = last_smoke() or {}
    inv = inventory()
    roles = {r["role"]: r["model"] for r in (inv.get("roles") or []) if r.get("present")}

    # Residual bonds: first-class next-session inputs
    bonds_text = ""
    bonds_meta: dict[str, Any] = {}
    bj: dict[str, Any] = {}
    try:
        from mag.bonds import BONDS_MD, ingest_bonds, load_bonds_json, load_bonds_text

        if refresh_bonds or not BONDS_MD.is_file():
            ingest_bonds(write=True)
        bonds_text = load_bonds_text(max_chars=max_bonds)
        bj = load_bonds_json() or {}
        bonds_meta = {
            "session_id": bj.get("session_id"),
            "n_loops": len(bj.get("open_loops") or []),
            "n_bonds": len(bj.get("residual_bonds") or []),
            "path": str(BONDS_MD),
        }
    except Exception as e:
        bonds_meta = {"error": str(e)}

    resonance_cards: list[dict[str, Any]] = []
    resonance_l0e = ""
    if cfg.get("include_resonance", True):
        try:
            from mag.resonance import format_l0e, top_cards

            goal_hint = (brief or "")[:200] + " " + " ".join(
                ln for ln in todo.splitlines() if ln.strip().startswith("- [ ]")
            )[:200]
            if goal:
                goal_hint = f"{goal[:200]} {goal_hint}"[:400]
            resonance_cards = top_cards(goal_hint, n=3)
            resonance_l0e = format_l0e(resonance_cards)
        except Exception:
            pass

    # open loops: prefer bonds, else crude from brief
    loops = list(bj.get("open_loops") or [])[:8]
    if not loops:
        for line in brief.splitlines():
            if line.strip().startswith("- ") and any(
                k in line.lower() for k in ("open", "next", "loop", "re-read", "check")
            ):
                loops.append(line.strip()[:160])
        loops = loops[:8]

    trail_excerpt: dict[str, Any] = {"active": False}
    if cfg.get("include_trail", True):
        try:
            from mag.run_trail import trail_pack_excerpt

            trail_excerpt = trail_pack_excerpt(max_events=12, max_chars=1600)
        except Exception as e:
            trail_excerpt = {"active": False, "error": str(e)}

    skills_excerpt = ""
    if cfg.get("include_skills", True):
        try:
            from mag.skills_pack import skills_for_job

            skills_excerpt = skills_for_job(job, max_chars=600)
        except Exception:
            skills_excerpt = ""

    ijl_skills = ""
    if cfg.get("include_ijl", True):
        try:
            from ijl_core import skill_excerpt_for_goal

            soft_goal = " ".join(
                [
                    goal[:200] if goal else "",
                    " ".join(loops[:3]) if loops else "",
                    (brief or "")[:200],
                ]
            ).strip() or "general harness dig"
            ijl_skills = skill_excerpt_for_goal(soft_goal, max_chars=500)
        except Exception as e:
            ijl_skills = f"(ijl skills: {e})"

    # Verkle tip badge — prove chain is live (LOAD continuity)
    tip_badge: dict[str, Any] = {"ok": False}
    dig_edges_n = 0
    try:
        tip_path = ROOT / "memory" / "biography" / "verkle_tip.json"
        if tip_path.is_file():
            tip = json.loads(tip_path.read_text(encoding="utf-8"))
            root = str(tip.get("root") or "")
            tip_badge = {
                "ok": True,
                "root_short": (root[:12] + "…") if len(root) > 12 else root,
                "n_leaves": tip.get("n_leaves"),
                "last_filename": tip.get("last_filename"),
                "last_session_id": tip.get("last_session_id"),
                "updated_minute": tip.get("updated_minute"),
            }
        res_dir = ROOT / "memory" / "biography" / "residual"
        if res_dir.is_dir():
            for p in res_dir.glob("*.json"):
                try:
                    o = json.loads(p.read_text(encoding="utf-8", errors="replace"))
                except Exception:
                    continue
                kind = str(o.get("kind") or "").lower()
                edges = o.get("edges") if isinstance(o.get("edges"), dict) else {}
                if kind in ("dig_leaf", "dig", "corpus_leaf") or edges.get("dig_leaf") or edges.get(
                    "dig_edges"
                ):
                    dig_edges_n += 1
                digs = edges.get("dig_leaves") or edges.get("related_digs") or []
                if isinstance(digs, list) and digs:
                    dig_edges_n += len(digs)
        tip_badge["dig_edges_n"] = dig_edges_n
    except Exception as e:
        tip_badge = {"ok": False, "error": str(e)}

    # Agent state (versioned Grok/Mag recall — not session tip)
    agent_state_excerpt = ""
    agent_state_meta: dict[str, Any] = {}
    try:
        from mag.agent_state import load_latest, pack_excerpt

        agent_state_excerpt = pack_excerpt(max_chars=900)
        lat = load_latest()
        if lat:
            agent_state_meta = {
                "label": lat.get("label"),
                "content_commit": ((lat.get("content_commit") or {}).get("hex") or "")[:16],
                "n_versions": (lat.get("tip") or {}).get("n_versions"),
                "path": "memory/agent_state/LATEST.md",
            }
    except Exception as e:
        agent_state_excerpt = f"(agent_state: {e})"
        agent_state_meta = {"error": str(e)}

    continuity_excerpt = ""
    try:
        cont = ROOT / "memory" / "working" / "OPERATOR_CONTINUITY.md"
        if cont.is_file():
            continuity_excerpt = cont.read_text(encoding="utf-8", errors="replace")[:2200]
    except Exception as e:
        continuity_excerpt = f"(continuity: {e})"

    nervous: dict[str, Any] = {}
    try:
        from mag.nervous_system import pack_excerpt

        nervous = pack_excerpt()
    except Exception as e:
        nervous = {"schema": "nervous_system.v1", "error": str(e)}

    # Behavioral loop + compass (teach tools — avoid re-approving the same mistakes)
    behavioral_excerpt = ""
    compass_framework = ""
    try:
        from mag.preferences import inject_behavioral_pack
        if inject_behavioral_pack():
            from mag.governance import _latest_behavioral_leaf
            from mag.compass import FRAMEWORK_BLOCK

            leaf = _latest_behavioral_leaf()
            if leaf.get("themes"):
                lines = ["[BEHAVIORAL — recurring errors to avoid (file-backed)]"]
                for t in leaf["themes"][:5]:
                    lines.append(f"- {t['id']}: {t['title']}")
                    if t.get("avoid"):
                        lines.append(f"  avoid: {t['avoid'][:160]}")
                lines.append(f"source: {leaf.get('path', 'memory/improve/daily/')}")
                behavioral_excerpt = "\n".join(lines)[:1200]
            compass_framework = FRAMEWORK_BLOCK[:900]
    except Exception:
        pass

    tesuji_excerpt = ""
    try:
        from mag.preferences import inject_behavioral_pack
        if inject_behavioral_pack():
            from mag.tesuji_shell import latest_leaf_excerpt

            leaf = latest_leaf_excerpt(max_wins=3)
            if leaf.get("wins"):
                lines = ["[TESUJI SHELLS — emergent wins to repeat (file-backed)]"]
                for w in leaf["wins"]:
                    lines.append(f"- {w['id']}: {w['title']}")
                    if w.get("surprise"):
                        lines.append(f"  surprise: {w['surprise'][:140]}")
                    if w.get("maps_to") and w["maps_to"] != "unmapped":
                        lines.append(f"  maps_to: {w['maps_to']}")
                lines.append(f"source: {leaf.get('path', 'memory/improve/daily/')}")
                tesuji_excerpt = "\n".join(lines)[:900]
    except Exception:
        pass

    coordination_excerpt = ""
    if cfg.get("include_coordination", True):
        try:
            from mag.coordination import format_activity_excerpt

            coordination_excerpt = format_activity_excerpt(limit=6, max_chars=900)
        except Exception:
            coordination_excerpt = ""
        try:
            from mag.tripartite_boot import format_tripartite_excerpt

            trip = format_tripartite_excerpt(max_chars=700)
            if trip:
                coordination_excerpt = (coordination_excerpt + "\n\n" + trip).strip()
        except Exception:
            pass
        try:
            from mag.peer_handoff import format_latest_brief

            peer = format_latest_brief()
            if peer and peer not in coordination_excerpt:
                coordination_excerpt = (coordination_excerpt + "\n\n" + peer).strip()[:1600]
        except Exception:
            pass

    soft_goal = " ".join(
        [
            goal[:200] if goal else "",
            " ".join(loops[:3]) if loops else "",
            (brief or "")[:200],
        ]
    ).strip() or "general harness dig"
    try:
        from mag.preferences import inject_behavioral_pack
        if inject_behavioral_pack():
            from mag.decision_framework import format_tips_block, surface_tips

            tips_block = format_tips_block(surface_tips(goal=soft_goal))
            if tips_block:
                behavioral_excerpt = (behavioral_excerpt + "\n\n" + tips_block).strip()[:1400]
    except Exception:
        pass
    if tesuji_excerpt:
        behavioral_excerpt = (behavioral_excerpt + "\n\n" + tesuji_excerpt).strip()[:1800]
    mirror_voice_excerpt = ""
    clue_chain_excerpt = ""
    if cfg.get("include_mirror_clue", True):
        mirror_voice_excerpt = _mirror_voice_excerpt(soft_goal, max_chars=600)
        clue_chain_excerpt = _clue_chain_excerpt(max_chars=500)

    build_excerpt = ""
    if cfg.get("include_build"):
        build_excerpt = _read_build_excerpt(build_path, max_chars=4000)
        if not build_excerpt and scope_slug:
            slug = scope_slug
            for p in (ROOT / "docs" / "ref").glob(f"BUILD-{slug}.md"):
                build_excerpt = _read_build_excerpt(p, max_chars=4000)
                break

    scope_excerpt = ""
    if cfg.get("include_scope"):
        scope_excerpt = _latest_scope_card(slug=scope_slug)

    pack = {
        "schema": "mag_context_pack.v1",
        "mode": mode,
        "job": job,
        "pack_max_chars": cfg.get("max_chars"),
        "ts": datetime.now(timezone.utc).isoformat(),
        "for": "grok_tui_router",
        "token_note": "Use this instead of chat_history. Escalate only hard work.",
        "operator_path": "FIND → FILE → LOAD (docs/ref/OPERATOR_CARD.md)",
        "layers": ["L0_nervous", "L0_policy", "L0e_resonance", "L0c_directives", "L1_bonds", "L2_trail", "L3_task", "L4_heat"],
        "nervous_system": nervous,
        "tip": tip_badge,
        "agent_state": agent_state_excerpt,
        "agent_state_meta": agent_state_meta,
        "continuity": continuity_excerpt,
        "health": {
            "status": s.get("status"),
            "live_stale": (s.get("recording") or {}).get("live_stale"),
            "port_8765": (s.get("integral") or {}).get("port_8765"),
        },
        "models": {
            "clerk": roles.get("clerk") or roles.get("router"),
            "worker": roles.get("worker"),
            "multi_smoke_ok": smoke.get("ok"),
            "multi_smoke_models": smoke.get("models_seen"),
        },
        "brief": brief or "(no brief — run: mag.cmd brief)",
        "bonds": bonds_text or "(no bonds — run: mag.cmd bonds)",
        "bonds_meta": bonds_meta,
        "open_loops": loops,
        "run_trail": trail_excerpt,
        "skills_excerpt": skills_excerpt,
        "ijl_skills": ijl_skills,
        "mirror_voice_excerpt": mirror_voice_excerpt,
        "clue_chain_excerpt": clue_chain_excerpt,
        "build_excerpt": build_excerpt,
        "scope_excerpt": scope_excerpt,
        "behavioral_excerpt": behavioral_excerpt,
        "compass_framework": compass_framework,
        "coordination_excerpt": coordination_excerpt,
        "resonance_cards": resonance_cards,
        "resonance_l0e": resonance_l0e,
        "live_tail": live or "(no live board)",
        "attention_tail": att[:400] if att else "",
        "directives": directives or "",
        "todo_open": [
            ln.strip()
            for ln in todo.splitlines()
            if ln.strip().startswith("- [ ]")
        ][:12],
        "commands": {
            "load": "mag.cmd context-pack",
            "ask": 'mag.cmd ask "…"',
            "bonds": "mag.cmd bonds",
            "trail": 'mag.cmd trail start "goal" --seat local --proactivity narrow',
            "route": 'mag.cmd route "…"',
            "lab": "mag.cmd lab",
            "smoke": "mag.cmd multi-smoke",
        },
    }
    return pack


def infer_pack_mode(goal: str = "", *, depth: str = "") -> str:
    """Pick pack mode from goal tags and route depth."""
    g = (goal or "").lower()
    d = (depth or "").lower()
    if g.startswith("[steward]") or d == "scut":
        return "janitor"
    if "[build]" in g or d in ("heavy_code", "simple_code"):
        return "build"
    if "audit" in g or d == "audit":
        return "audit"
    if "[priority]" in g or d == "plan":
        return "plan"
    if d in ("overview", "route"):
        return "route"
    return "full"


def format_context_pack_text(
    pack: dict[str, Any] | None = None,
    *,
    mode: str | None = None,
    max_chars: int | None = None,
) -> str:
    """Layered pack: policy → bonds → trail cores → task → heat (drop heat first)."""
    p = pack or build_context_pack()
    mode = _normalize_mode(mode or p.get("mode"))
    cfg = MODE_CONFIG[mode]
    max_chars = max_chars if max_chars is not None else int(cfg.get("max_chars") or 4500)
    compact_ns = bool(cfg.get("compact_nervous"))
    tip = p.get("tip") or {}
    tip_line = (
        f"- tip: {tip.get('root_short')} · leaves={tip.get('n_leaves')} · "
        f"last={tip.get('last_filename')} · dig_edges={tip.get('dig_edges_n', 0)}"
        if tip.get("ok")
        else f"- tip: (unavailable) {tip.get('error') or ''}"
    )
    as_meta = p.get("agent_state_meta") or {}
    as_line = (
        f"- agent_state: label={as_meta.get('label')} commit={as_meta.get('content_commit')} "
        f"n={as_meta.get('n_versions')} · LOAD before redesign"
        if as_meta.get("label")
        else "- agent_state: (none — main.py agent-state --commit)"
    )
    ns = p.get("nervous_system") or {}
    body = ns.get("body") or {}
    keys_line = ns.get("keys_line") or ""
    if not keys_line:
        key_bits = []
        for row in ns.get("keys") or []:
            if isinstance(row, dict):
                key_bits.append(f"{row.get('id')}={row.get('status') or '—'}")
        keys_line = ", ".join(key_bits)
    ns_lines = [
        "### L0a Nervous system (agent ops subsystem — default LOAD)",
        f"- body_ok={ns.get('ok')} integral_ok={ns.get('integral_ok')}",
        f"- dash:8765={'UP' if body.get('dashboard_8765') else 'DOWN'} · "
        f"ollama={'UP' if body.get('ollama_11434') else 'DOWN'} · "
        f"smoke={'PASS' if body.get('multi_smoke_ok') else 'FAIL'}",
    ]
    if not compact_ns:
        ns_lines.extend([
            f"- session tip: {(ns.get('session_tip') or {}).get('root_short')}… "
            f"leaves={(ns.get('session_tip') or {}).get('n_leaves')}",
            f"- agent tip: {(ns.get('agent_tip') or {}).get('root_short')}… "
            f"commit={(ns.get('agent_tip') or {}).get('commit8')}",
            f"- keys: {keys_line or '(none)'}",
            f"- note: {ns.get('note') or 'probe before claim seats'}",
            f"- face: {ns.get('path') or 'memory/nervous_system.md'} · CLI: main.py nervous",
        ])
    ns_lines.append("")
    policy = [
        f"# Mag context pack · mode={mode} ({p.get('ts', '')[:19]})",
        "",
        "## L0 Policy (stable — pack-first, residual DNA, seat purity)",
        f"- path: {p.get('operator_path') or 'FIND → FILE → LOAD'}",
        "- Use this pack only; do not reload full chat.",
        "- Remotes: pack+goal only. T0/T1 never remote.",
        tip_line,
        f"- health: {p.get('health')}",
        "",
        *ns_lines,
    ]
    if mode != "janitor":
        policy.extend([
            as_line,
            f"- models: {p.get('models')}",
            f"- bonds_meta: {p.get('bonds_meta')}",
        ])
    if mode not in ("janitor", "route"):
        policy.extend([
            "",
            "### L0b Agent state (versioned self — Verkle agent tip)",
            p.get("agent_state") or "(none)",
        ])
        if p.get("continuity"):
            policy.extend([
                "",
                "### L0-continuity (goals · gaps · eject · smokes — cold Grok must use this)",
                "path: memory/working/OPERATOR_CONTINUITY.md",
                p.get("continuity"),
            ])
    if p.get("directives") and mode in ("plan", "full"):
        policy.extend([
            "",
            "### L0c Operator directives (autonomy contract — operator-set, stable)",
            p.get("directives") or "(none yet — memory/operator_directives.md)",
        ])
    if p.get("behavioral_excerpt") and mode not in ("janitor",):
        policy.extend(["", p.get("behavioral_excerpt")])
    if p.get("coordination_excerpt") and mode in ("route", "build", "audit", "plan", "full"):
        policy.extend(["", p.get("coordination_excerpt")])
    if p.get("resonance_l0e") and cfg.get("include_resonance"):
        policy.extend(["", p.get("resonance_l0e")])
    bonds = []
    if mode != "janitor" or (p.get("bonds") and "(no bonds" not in str(p.get("bonds"))):
        bonds = [
            "",
            "## L1 Bonds (next-session / residual edges)",
            (p.get("bonds") or "(none — run: python main.py bonds)")[:800 if mode == "janitor" else 5000],
        ]
    skills = []
    if cfg.get("include_skills") and p.get("skills_excerpt"):
        skills = [
            "",
            "## L1b Skills (progressive — not MCP flood)",
            p.get("skills_excerpt") or "(none — configs/skills.yaml)",
        ]
        if cfg.get("include_ijl") and p.get("ijl_skills"):
            skills.extend([
                "",
                "### L1b IJL skill beads (episode distill)",
                p.get("ijl_skills") or "(none yet)",
            ])
    if p.get("mirror_voice_excerpt"):
        skills.extend(["", "### L1c Mirror voice (operator corpus)", p.get("mirror_voice_excerpt")])
    if p.get("clue_chain_excerpt"):
        skills.extend(["", "### L1c Clue chain", p.get("clue_chain_excerpt")])

    build_block = []
    if p.get("build_excerpt"):
        build_block = [
            "",
            "## L2b Frozen BUILD (builder seat — do not mutate spec)",
            p.get("build_excerpt") or "",
        ]
    scope_block = []
    if p.get("scope_excerpt"):
        scope_block = [
            "",
            "## L2c Scope card (steward — dumb-agent brief)",
            p.get("scope_excerpt") or "",
        ]

    trail = []
    if cfg.get("include_trail"):
        trail = [
            "",
            "## L2 Trail cores (mid-run continuity — re-inject)",
            (p.get("run_trail") or {}).get("text")
            or "(no open run — python main.py trail start \"goal\")",
        ]
    task = [
        "",
        "## L3 Task (brief + loops + todo)",
        "### Brief",
        (p.get("brief") or "")[:400 if mode == "janitor" else 5000],
        "",
        "### Open loops",
        "\n".join(p.get("open_loops") or ["(none extracted)"])[:400 if mode == "janitor" else 2000],
    ]
    if mode not in ("janitor",):
        task.extend([
            "",
            "### Todo open",
            "\n".join(p.get("todo_open") or ["(none)"]),
        ])
    heat = []
    if cfg.get("include_heat"):
        heat = [
            "",
            "## L4 Heat (drop first under compaction)",
            "### Live tail",
            p.get("live_tail") or "",
            "",
            "### Attention",
            p.get("attention_tail") or "",
            "",
            "_Grok: answer from this. Re-inject trail cores if run active._",
        ]
    parts = [policy, bonds, skills, build_block, scope_block, trail, task, heat]
    text = "\n".join("\n".join(x) for x in parts)
    if len(text) > max_chars:
        # The frozen BUILD and scope are the worker's actual contract; never
        # discard them while retaining contextual history.
        parts = [policy, build_block, scope_block, bonds, skills, trail, task]  # drop L4 heat
        text = "\n".join("\n".join(x) for x in parts)
    if len(text) > max_chars:
        brief = (p.get("brief") or "")[:800]
        task_small = [
            "",
            "## L3 Task (compacted)",
            "### Brief",
            brief + ("…" if len(p.get("brief") or "") > 800 else ""),
            "",
            "### Open loops",
            "\n".join((p.get("open_loops") or [])[:5] or ["(none)"]),
        ]
        text = "\n".join(
            "\n".join(x) for x in [policy, build_block, scope_block, bonds, skills, trail, task_small]
        )
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n…(pack clipped)"
    return text


def format_agent_preamble(
    pack: dict[str, Any] | None = None,
    *,
    goal: str = "",
    max_chars: int = 2200,
) -> str:
    """Blind-men coarse elephant for subagents/workflow workers.

    Nervous + tip + open loops + trail cores + optional goal.
    No L4 heat, no full bonds dump, no residual DNA.
    Law: docs/ref/COORDINATION_ELIAS_ROPE.md
    """
    p = pack or build_context_pack()
    tip = p.get("tip") or {}
    tip_line = (
        f"tip={tip.get('root_short')} leaves={tip.get('n_leaves')} "
        f"last={tip.get('last_filename')}"
        if tip.get("ok")
        else f"tip=unavailable {tip.get('error') or ''}"
    )
    ns = p.get("nervous_system") or {}
    body = ns.get("body") or {}
    keys_line = ns.get("keys_line") or ""
    if not keys_line:
        key_bits = []
        for row in ns.get("keys") or []:
            if isinstance(row, dict):
                key_bits.append(f"{row.get('id')}={row.get('status') or '—'}")
        keys_line = ", ".join(key_bits)
    loops = p.get("open_loops") or []
    loops_txt = "\n".join(f"- {x}" for x in loops[:6]) if loops else "- (none)"
    trail = p.get("run_trail") or {}
    trail_txt = trail.get("text") or "(no open run)"
    if len(trail_txt) > 700:
        trail_txt = trail_txt[:700] + "…"
    base_id = trail.get("base_id") or (trail.get("base") or {}).get("base_id") or ""
    base_tip = (trail.get("base") or {}).get("tip_root_short") or ""
    base_git = (trail.get("base") or {}).get("git_sha") or ""
    goal_block = (goal or "").strip()[:500]
    lines = [
        "# Mag agent preamble (coarse elephant — not DNA)",
        f"# ts={(p.get('ts') or '')[:19]} · law=COORDINATION_ELIAS_ROPE",
        "",
        "## Contract",
        "- Trust this pack + your task boundary. Do not invent body/keys/status.",
        "- Do not load full residual or chat history. Deep probe only if task requires a path.",
        "- FILE progress as trail drift cores (base_id + locus), not peer chat.",
        "- Remotes: pack+goal only. No T0/T1 private archive paths.",
        "",
        "## Base (frozen graph — cite in every drift)",
        f"- base_id: {base_id or '(no open run — trail start first)'}",
        f"- tip: {base_tip or '—'} · git: {base_git or '—'}",
        "- Drift without this base_id is rejected by architecture.",
        "",
        "## Goal (if provided)",
        goal_block or "(orchestrator supplies goal in task prompt)",
        "",
        "## L0a Nervous",
        f"- body_ok={ns.get('ok')} integral_ok={ns.get('integral_ok')}",
        f"- dash:8765={'UP' if body.get('dashboard_8765') else 'DOWN'} · "
        f"ollama={'UP' if body.get('ollama_11434') else 'DOWN'} · "
        f"smoke={'PASS' if body.get('multi_smoke_ok') else 'FAIL'}",
        f"- session tip: {(ns.get('session_tip') or {}).get('root_short')} "
        f"leaves={(ns.get('session_tip') or {}).get('n_leaves')}",
        f"- agent tip: {(ns.get('agent_tip') or {}).get('root_short')} "
        f"commit={(ns.get('agent_tip') or {}).get('commit8')}",
        f"- keys: {keys_line or '(none)'} · probe before claim seats",
        f"- {tip_line}",
        "",
        "## Open loops (narrow)",
        loops_txt,
        "",
        "## Trail cores (mid-run — re-inject)",
        trail_txt,
        "",
        "_Worker: complete task from tools + this preamble. Empty findings only after real inspection._",
    ]
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n…(preamble clipped)"
    return text
