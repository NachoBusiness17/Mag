"""Agent state for LangGraph."""
from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    goal: str
    tier: str  # T0|T1|T2|T3
    plan: list[str]
    step_i: int
    tool_trace: list[dict[str, Any]]
    critique: str
    route: str  # direct|plan|escalate|wait
    handoff_id: str | None
    status: str  # running|done|blocked|escalated|waiting
    success_checks: list[str]
    last_result: str
    retry_count: int
    thread_id: str
    # IJL-v0 (PlanSearch-lite + process value + skill beads)
    observations: list[str]
    alt_plans: list[list[str]]
    plan_index: int
    process_value: dict[str, Any]
    value_trace: list[dict[str, Any]]
    task_family: str
    skill_bead_path: str
