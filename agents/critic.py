"""Critic / process-value node (IJL mid-trajectory judgment)."""
from __future__ import annotations

from audit import log_event, sync_current
from config import PROMPTS_DIR
from llm import chat, extract_json
from ijl_core import (
    infer_task_family,
    map_value_to_decision,
    normalize_value,
    write_skill_bead,
)
from state import AgentState


def critic_node(state: AgentState) -> dict:
    goal = state.get("goal") or ""
    last = state.get("last_result") or ""
    checks = state.get("success_checks") or []
    retries = int(state.get("retry_count") or 0)
    plan = state.get("plan") or []
    step_i = int(state.get("step_i") or 0)
    value_trace = list(state.get("value_trace") or [])
    task_family = state.get("task_family") or infer_task_family(goal)

    system = (
        (PROMPTS_DIR / "critic.txt").read_text(encoding="utf-8")
        if (PROMPTS_DIR / "critic.txt").is_file()
        else (
            'JSON: {"value":{"valence":"mixed","intensity":0.5,"stuck":false,'
            '"capture_flags":[],"tier_ok":true,"short_circuit":false,"reason":"",'
            '"next":"continue"},"decision":"done","critique":"..."}'
        )
    )
    decision = "done"
    critique = ""
    value = normalize_value({})
    try:
        raw = chat(
            "critic",
            system,
            f"Goal: {goal}\nTier: {state.get('tier')}\nTask family: {task_family}\n"
            f"Plan step_i={step_i}/{len(plan)} plan={plan}\n"
            f"Alt plans remaining: "
            f"{max(0, len(state.get('alt_plans') or []) - int(state.get('plan_index') or 0) - 1)}\n"
            f"Checks: {checks}\n"
            f"Tool/result:\n{last[:4000]}\nRetries: {retries}\n"
            f"Observations: {(state.get('observations') or [])[:6]}",
        )
        data = extract_json(raw) or {}
        decision = str(data.get("decision") or "done").lower()
        critique = str(data.get("critique") or raw[:500])
        value = normalize_value(data.get("value") if isinstance(data.get("value"), dict) else data)
    except Exception as e:
        critique = f"critic error: {e}"
        trace = state.get("tool_trace") or []
        if trace and any(t.get("ok") for t in trace):
            decision = "done"
            value = normalize_value({"valence": "mixed", "next": "continue", "reason": "fallback ok"})
        else:
            decision = "escalate" if retries >= 1 else "continue"
            value = normalize_value(
                {
                    "valence": "bad",
                    "stuck": True,
                    "short_circuit": retries >= 1,
                    "next": "escalate" if retries >= 1 else "continue",
                    "reason": "fallback no tool ok",
                }
            )

    trace = state.get("tool_trace") or []
    has_tool_ok = any(t.get("ok") for t in trace)
    decision = map_value_to_decision(
        value,
        base_decision=decision,
        step_i=step_i,
        plan_len=len(plan),
        retries=retries,
        has_tool_ok=has_tool_ok,
    )

    if decision not in {"continue", "replan", "done", "escalate", "wait"}:
        decision = "done"

    # More steps left and continue
    if decision == "continue" and step_i >= max(len(plan), 1) and retries >= 1:
        decision = "done"
    if decision == "replan":
        retries += 1
        if retries > 2:
            decision = "escalate"

    # never free-escalate without priority tag
    if decision == "escalate":
        from mag.lanes import text_has_priority

        blob = f"{goal}\n{critique}\n{value.get('reason') or ''}"
        if not text_has_priority(blob):
            # if alt plans remain, replan instead of escalate
            alts = state.get("alt_plans") or []
            pidx = int(state.get("plan_index") or 0)
            if pidx + 1 < len(alts) and retries <= 2:
                decision = "replan"
            else:
                decision = "wait" if not has_tool_ok else "done"
                critique = (
                    f"(escalate blocked — no [priority]/[grok]) {critique}"
                )

    status = {
        "done": "done",
        "escalate": "escalated",
        "wait": "waiting",
        "continue": "running",
        "replan": "running",
    }[decision]

    value_trace = value_trace + [value]
    skill_path = state.get("skill_bead_path") or ""

    if decision == "done" and has_tool_ok:
        try:
            p = write_skill_bead(
                goal=goal,
                plan=list(plan),
                success_checks=list(checks),
                critique=critique,
                value_trace=value_trace,
                tool_ok_count=sum(1 for t in trace if t.get("ok")),
                task_family=task_family,
                parent_run=state.get("thread_id"),
            )
            if p:
                skill_path = str(p)
        except Exception as e:
            log_event({"node": "critic", "skill_bead_error": str(e)})

    out = {
        "critique": f"[{decision}] {critique}",
        "status": status,
        "retry_count": retries,
        "process_value": value,
        "value_trace": value_trace[-20:],
        "task_family": task_family,
        "skill_bead_path": skill_path,
        "route": "escalate" if decision == "escalate" else state.get("route"),
        "last_result": last,
    }

    log_event(
        {
            "node": "critic",
            "decision": decision,
            "status": status,
            "retries": retries,
            "value": value,
            "skill_bead": skill_path or None,
        }
    )
    sync_current({**state, **{k: v for k, v in out.items()}})
    return out
