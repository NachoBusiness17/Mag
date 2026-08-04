"""Executor — pick and run tools for current plan step."""
from __future__ import annotations

import re
from typing import Any

from audit import log_event, sync_current
from llm import chat, extract_json
from state import AgentState
from tools import dispatch


def _heuristic_tools(goal: str, step: str) -> list[dict[str, Any]]:
    text = f"{goal}\n{step}".lower()
    actions: list[dict[str, Any]] = []
    # list / dir
    m = re.search(r"(?:list|ls|dir)\s+(?:files?\s+)?(?:under|in)?\s*[`'\"]?([^\s`'\"]+)", text)
    if m:
        actions.append({"tool": "list_dir", "args": {"path": m.group(1)}})
    elif re.search(r"\b(list|ls|dir)\b", text) and "memory" in text:
        actions.append({"tool": "list_dir", "args": {"path": "memory"}})
    elif re.search(r"\b(list|ls|dir)\b", text):
        actions.append({"tool": "list_dir", "args": {"path": "."}})

    # read
    m = re.search(r"read\s+[`'\"]?([^\s`'\"]+\.\w+)", text)
    if m:
        actions.append({"tool": "read_file", "args": {"path": m.group(1)}})
    if "current.md" in text or "summarize current" in text:
        actions.append({"tool": "read_file", "args": {"path": "state/CURRENT.md"}})
    if "locus" in text:
        actions.append({"tool": "read_file", "args": {"path": "memory/locus.md"}})

    if not actions and "python" in text:
        actions.append({"tool": "run_python", "args": {"code": "print(2+2)"}})
    if not actions:
        actions.append({"tool": "list_dir", "args": {"path": "."}})
    return actions


def executor_node(state: AgentState) -> dict:
    goal = state.get("goal") or ""
    plan = state.get("plan") or [goal]
    step_i = int(state.get("step_i") or 0)
    step = plan[step_i] if step_i < len(plan) else goal
    trace = list(state.get("tool_trace") or [])

    actions: list[dict[str, Any]] = []
    try:
        raw = chat(
            "worker",
            "You pick tools. JSON only: "
            '{"actions":[{"tool":"list_dir|read_file|write_file|search_files|run_shell|run_python",'
            '"args":{...}}]} '
            "Prefer minimal tools. Paths relative to project root.",
            f"Goal: {goal}\nStep: {step}\nPrior: {trace[-3:]}",
        )
        data = extract_json(raw) or {}
        actions = list(data.get("actions") or [])
    except Exception as e:
        log_event({"node": "executor", "error": str(e)})

    if not actions:
        actions = _heuristic_tools(goal, step)

    results_text: list[str] = []
    for act in actions[:4]:
        name = str(act.get("tool") or "")
        args = act.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        res = dispatch(name, args)
        entry = {
            "tool": name,
            "args": args,
            "ok": res.get("ok"),
            "exit_code": res.get("exit_code"),
            "output": (res.get("output") or res.get("error") or "")[:2000],
        }
        trace.append(entry)
        results_text.append(f"{name}: exit={entry['exit_code']}\n{entry['output']}")
        log_event({"node": "executor", "tool": name, "exit_code": entry["exit_code"], "ok": entry["ok"]})

    out = {
        "tool_trace": trace,
        "step_i": step_i + 1,
        "last_result": "\n---\n".join(results_text)[:6000],
        "status": "running",
    }
    sync_current({**state, **out})
    return out
