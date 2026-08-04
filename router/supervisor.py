"""Router node — classify goal → route + tier."""
from __future__ import annotations

import re
from pathlib import Path

from audit import log_event, sync_current
from config import PROMPTS_DIR
from llm import chat, extract_json
from state import AgentState


def _heuristic(goal: str) -> dict:
    g = goal.lower()
    tier = "T2"
    if any(k in g for k in ("secret", "password", "api key", ".env", "credential")):
        tier = "T0"
    elif any(k in g for k in ("data/raw", "private archive", "intimate")):
        tier = "T1"
    elif re.search(r"\b(escalate to grok|hand off to grok|architecture review)\b", g):
        tier = "T3"

    route = "plan"
    if re.search(r"\b(list|read|show|cat|ls|dir|write)\b", g) and len(g) < 160:
        route = "direct" if "write" not in g else "plan"
    if re.search(r"\b(list|read|show|cat|ls|dir)\b", g) and "write" not in g and len(g) < 160:
        route = "direct"
    if any(k in g for k in ("multi-step", "refactor", "implement", "design system")):
        route = "plan"
    if re.search(r"\b(hand off to grok|escalate to grok)\b", g):
        route = "escalate"
        tier = "T3"
    if "wait for me" in g or "ask human" in g:
        route = "wait"
    return {"route": route, "tier": tier, "rationale": "heuristic"}


def router_node(state: AgentState) -> dict:
    goal = state.get("goal") or ""
    prompt_path = PROMPTS_DIR / "router.txt"
    system = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else (
        "Classify the goal. Reply JSON only: "
        '{"route":"direct|plan|escalate|wait","tier":"T0|T1|T2|T3","rationale":"..."}'
    )
    parsed = None
    try:
        raw = chat("router", system, f"Goal:\n{goal}")
        parsed = extract_json(raw)
    except Exception as e:
        log_event({"node": "router", "error": str(e), "fallback": True})

    h = _heuristic(goal)
    if parsed:
        route = str(parsed.get("route") or h["route"]).lower()
        tier = str(parsed.get("tier") or h["tier"]).upper()
        if route not in {"direct", "plan", "escalate", "wait"}:
            route = h["route"]
        if tier not in {"T0", "T1", "T2", "T3"}:
            tier = h["tier"]
        # Model must not invent T0 — only keyword heuristic can set T0
        if tier == "T0" and h["tier"] != "T0":
            tier = h["tier"]
        # Model must not invent T1 over public work
        if tier == "T1" and h["tier"] == "T2":
            tier = "T2"
        if h["tier"] == "T0":
            tier = "T0"
        rationale = str(parsed.get("rationale") or "model")[:200]
    else:
        route, tier, rationale = h["route"], h["tier"], h["rationale"]

    # Prefer heuristic route for obvious list/read (small models drift)
    if h["route"] == "direct" and route in {"wait", "escalate"}:
        route = "direct"
        rationale = f"{rationale}+force_direct"
    if h["route"] == "plan" and route == "wait" and h["tier"] != "T0":
        route = "plan"
        rationale = f"{rationale}+force_plan"

    # Constitutional: real T0 only — block to wait
    if tier == "T0" and h["tier"] == "T0":
        route = "wait"

    out = {
        "route": route,
        "tier": tier,
        "status": "running",
        "retry_count": state.get("retry_count") or 0,
        "step_i": state.get("step_i") or 0,
        "tool_trace": state.get("tool_trace") or [],
        "plan": state.get("plan") or [],
        "last_result": f"routed:{route} tier:{tier} ({rationale})",
    }
    log_event({"node": "router", "goal": goal[:200], "route": route, "tier": tier, "rationale": rationale})
    sync_current({**state, **out})
    return out
