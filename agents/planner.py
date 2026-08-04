"""Planner node — PlanSearch-lite (k diverse plans + alt replan)."""
from __future__ import annotations

from audit import log_event, sync_current
from config import PROMPTS_DIR
from llm import chat, extract_json
from ijl_core import (
    infer_task_family,
    mean_pairwise_diversity,
    next_alt_plan,
    normalize_plans,
    pick_primary_plan_index,
    skill_excerpt_for_goal,
)
from state import AgentState


def planner_node(state: AgentState) -> dict:
    goal = state.get("goal") or ""
    task_family = state.get("task_family") or infer_task_family(goal)
    retry = int(state.get("retry_count") or 0)

    # PlanSearch-lite: on replan, prefer unused alt strategies before new LLM call
    if retry > 0:
        alt_plan, new_idx = next_alt_plan(
            list(state.get("alt_plans") or []),
            int(state.get("plan_index") or 0),
        )
        if alt_plan:
            out = {
                "plan": alt_plan,
                "plan_index": new_idx,
                "step_i": 0,
                "status": "running",
                "task_family": task_family,
                "last_result": f"alt plan {new_idx + 1}/{len(state.get('alt_plans') or [])}: "
                + " | ".join(alt_plan),
            }
            log_event(
                {
                    "node": "planner",
                    "mode": "alt_plan",
                    "plan_index": new_idx,
                    "plan": alt_plan,
                }
            )
            sync_current({**state, **out})
            return out

    system = (
        (PROMPTS_DIR / "planner.txt").read_text(encoding="utf-8")
        if (PROMPTS_DIR / "planner.txt").is_file()
        else (
            "JSON: "
            '{"observations":[],"plans":[["step"]],"success_checks":["..."]}'
        )
    )
    plan: list[str] = []
    alt_plans: list[list[str]] = []
    observations: list[str] = []
    checks = list(state.get("success_checks") or [])
    skill_hint = ""
    try:
        skill_hint = skill_excerpt_for_goal(goal, max_chars=500)
    except Exception:
        skill_hint = ""

    user = f"Goal:\n{goal}\nTier: {state.get('tier')}\nTask family: {task_family}\n"
    if skill_hint:
        user += f"\nPrior skill beads (LOAD):\n{skill_hint}\n"
    if state.get("critique"):
        user += f"\nPrior critique (replan):\n{(state.get('critique') or '')[:800]}\n"

    try:
        raw = chat("worker", system, user)
        data = extract_json(raw) or {}
        observations = [str(x) for x in (data.get("observations") or [])][:8]
        # Prefer multi-plan; fall back to single "plan" key
        if data.get("plans"):
            alt_plans = normalize_plans(data.get("plans"), max_plans=3, max_steps=6)
        elif data.get("plan"):
            alt_plans = normalize_plans(data.get("plan"), max_plans=1, max_steps=6)
        if data.get("success_checks"):
            checks = [str(x) for x in data["success_checks"]]
    except Exception as e:
        log_event({"node": "planner", "error": str(e)})

    if not alt_plans:
        alt_plans = [[f"Use tools to accomplish: {goal}"]]
    idx = pick_primary_plan_index(alt_plans)
    # order so primary is index 0 for simple progression; keep full set as alts
    if idx != 0 and len(alt_plans) > 1:
        primary = alt_plans[idx]
        rest = [p for i, p in enumerate(alt_plans) if i != idx]
        alt_plans = [primary] + rest
        idx = 0
    plan = list(alt_plans[0])
    if not checks:
        checks = ["Goal addressed with tool evidence or clear answer"]

    out = {
        "plan": plan,
        "alt_plans": alt_plans,
        "plan_index": idx,
        "observations": observations,
        "success_checks": checks,
        "step_i": 0,
        "status": "running",
        "task_family": task_family,
        "last_result": "plan ready: " + " | ".join(plan),
    }
    log_event(
        {
            "node": "planner",
            "mode": "plansearch",
            "n_plans": len(alt_plans),
            "diversity": mean_pairwise_diversity(alt_plans),
            "plan": plan,
            "checks": checks,
            "observations": observations[:5],
        }
    )
    sync_current({**state, **out})
    return out
