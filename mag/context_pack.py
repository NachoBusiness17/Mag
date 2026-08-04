"""Minimum-token pack for Grok (this TUI) — never full chat."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT


def _clip(path: Path, n: int) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:n]


def build_context_pack(
    *,
    max_brief: int = 1200,
    max_live: int = 800,
    max_bonds: int = 1600,
    refresh_bonds: bool = False,
) -> dict[str, Any]:
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

    # open loops: prefer bonds, else crude from brief
    loops = list(bj.get("open_loops") or [])[:8]
    if not loops:
        for line in brief.splitlines():
            if line.strip().startswith("- ") and any(
                k in line.lower() for k in ("open", "next", "loop", "re-read", "check")
            ):
                loops.append(line.strip()[:160])
        loops = loops[:8]

    # Live run trail (mid-run continuity; pack-first, not full chat)
    trail_excerpt: dict[str, Any] = {"active": False}
    try:
        from mag.run_trail import trail_pack_excerpt

        trail_excerpt = trail_pack_excerpt(max_events=12, max_chars=1600)
    except Exception as e:
        trail_excerpt = {"active": False, "error": str(e)}

    # Progressive skills excerpts (configs/skills.yaml) — not full skill flood
    skills_excerpt = ""
    try:
        from mag.skills_pack import skills_for_job

        skills_excerpt = skills_for_job("default", max_chars=600)
    except Exception:
        skills_excerpt = ""

    # IJL skill beads (learned episodes) — residual pins, not chat
    ijl_skills = ""
    try:
        from ijl_core import skill_excerpt_for_goal

        # prefer open loop / todo keywords as soft goal for LOAD
        soft_goal = " ".join(
            [
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

    pack = {
        "schema": "mag_context_pack.v1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "for": "grok_tui_router",
        "token_note": "Use this instead of chat_history. Escalate only hard work.",
        "operator_path": "FIND → FILE → LOAD (docs/ref/OPERATOR_CARD.md)",
        "layers": ["L0_nervous", "L0_policy", "L0c_directives", "L1_bonds", "L2_trail", "L3_task", "L4_heat"],
        "nervous_system": nervous,
        "tip": tip_badge,
        "agent_state": agent_state_excerpt,
        "agent_state_meta": agent_state_meta,
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
        "behavioral_excerpt": behavioral_excerpt,
        "compass_framework": compass_framework,
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


def format_context_pack_text(
    pack: dict[str, Any] | None = None,
    *,
    max_chars: int = 4500,
) -> str:
    """Layered pack: policy → bonds → trail cores → task → heat (drop heat first)."""
    p = pack or build_context_pack()
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
        f"- session tip: {(ns.get('session_tip') or {}).get('root_short')}… "
        f"leaves={(ns.get('session_tip') or {}).get('n_leaves')}",
        f"- agent tip: {(ns.get('agent_tip') or {}).get('root_short')}… "
        f"commit={(ns.get('agent_tip') or {}).get('commit8')}",
        f"- keys: {keys_line or '(none)'}",
        f"- note: {ns.get('note') or 'probe before claim seats'}",
        f"- face: {ns.get('path') or 'memory/nervous_system.md'} · CLI: main.py nervous",
        "",
    ]
    policy = [
        f"# Mag context pack ({p.get('ts', '')[:19]})",
        "",
        "## L0 Policy (stable — pack-first, residual DNA, seat purity)",
        f"- path: {p.get('operator_path') or 'FIND → FILE → LOAD'}",
        "- Use this pack only; do not reload full chat.",
        "- Remotes: pack+goal only. T0/T1 never remote.",
        "- Active run: re-inject trail cores; do not swap seat mid-run.",
        "- Process lessons → playbook; case facts → residual; mid-goal → trail.",
        "- Kimi-style: trail integrity + artifact>transcript (contracts, not remote seat).",
        "- **Do not reinvent:** LOAD agent_state before redesigning Mag/republic loops.",
        "- **Nervous system first:** L0a glance before inventing keys/online/status.",
        tip_line,
        as_line,
        f"- health: {p.get('health')}",
        f"- models: {p.get('models')}",
        f"- bonds_meta: {p.get('bonds_meta')}",
        "",
        *ns_lines,
        "### L0b Agent state (versioned self — Verkle agent tip)",
        p.get("agent_state") or "(none)",
        "",
        "### L0c Operator directives (autonomy contract \u2014 operator-set, stable)",
        p.get("directives") or "(none yet \u2014 memory/operator_directives.md)",
    ]
    if p.get("compass_framework"):
        policy.extend(["", "### L0d Compass framework (steering + autonomous continue)", p.get("compass_framework")])
    if p.get("behavioral_excerpt"):
        policy.extend(["", p.get("behavioral_excerpt")])
    bonds = [
        "",
        "## L1 Bonds (next-session / residual edges)",
        p.get("bonds") or "(none — run: python main.py bonds)",
    ]
    skills = [
        "",
        "## L1b Skills (progressive — not MCP flood)",
        p.get("skills_excerpt") or "(none — configs/skills.yaml)",
        "",
        "### L1b IJL skill beads (episode distill)",
        p.get("ijl_skills") or "(none yet — successful runs FILE beads under memory/improve/pins/skills/)",
    ]
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
        p.get("brief") or "",
        "",
        "### Open loops",
        "\n".join(p.get("open_loops") or ["(none extracted)"]),
        "",
        "### Todo open",
        "\n".join(p.get("todo_open") or ["(none)"]),
    ]
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
    # Assemble; drop heat then shrink task if over max_chars
    parts = [policy, bonds, skills, trail, task, heat]
    text = "\n".join("\n".join(x) for x in parts)
    if len(text) > max_chars:
        parts = [policy, bonds, skills, trail, task]  # drop L4 heat
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
            "\n".join(x) for x in [policy, bonds, skills, trail, task_small]
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
