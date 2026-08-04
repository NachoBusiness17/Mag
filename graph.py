"""LangGraph StateGraph: router → planner/executor → critic → end/escalate/wait."""
from __future__ import annotations

from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.critic import critic_node
from agents.escalate_grok import escalate_grok_node
from agents.executor import executor_node
from agents.planner import planner_node
from agents.wait_human import wait_human_node
from router.supervisor import router_node
from state import AgentState


def _after_router(state: AgentState) -> Literal["planner", "executor", "escalate_grok", "wait_human"]:
    route = (state.get("route") or "plan").lower()
    if route == "escalate":
        return "escalate_grok"
    if route == "wait":
        return "wait_human"
    if route == "direct":
        # ensure plan has one step
        return "executor"
    return "planner"


def _after_critic(state: AgentState) -> Literal["executor", "planner", "escalate_grok", "wait_human", "__end__"]:
    critique = state.get("critique") or ""
    # decision embedded as [decision] prefix
    decision = "done"
    if critique.startswith("["):
        end = critique.find("]")
        if end > 0:
            decision = critique[1:end].lower()
    status = state.get("status") or ""
    if status == "escalated" or decision == "escalate":
        return "escalate_grok"
    if status == "waiting" or decision == "wait":
        return "wait_human"
    if decision == "replan":
        return "planner"
    if decision == "continue":
        return "executor"
    return "__end__"


def _ensure_plan_for_direct(state: AgentState) -> dict:
    """Before direct executor, inject a one-step plan if missing."""
    if state.get("plan"):
        return {}
    return {
        "plan": [state.get("goal") or "do task"],
        "success_checks": state.get("success_checks")
        or ["Tool evidence produced or clear answer"],
        "step_i": 0,
    }


def build_graph(checkpointer: Any | None = None):
    g = StateGraph(AgentState)
    g.add_node("router", router_node)
    g.add_node("ensure_direct", _ensure_plan_for_direct)
    g.add_node("planner", planner_node)
    g.add_node("executor", executor_node)
    g.add_node("critic", critic_node)
    g.add_node("escalate_grok", escalate_grok_node)
    g.add_node("wait_human", wait_human_node)

    g.add_edge(START, "router")

    def route_dispatch(state: AgentState):
        r = _after_router(state)
        if r == "executor":
            return "ensure_direct"
        return r

    g.add_conditional_edges(
        "router",
        route_dispatch,
        {
            "ensure_direct": "ensure_direct",
            "planner": "planner",
            "escalate_grok": "escalate_grok",
            "wait_human": "wait_human",
        },
    )
    g.add_edge("ensure_direct", "executor")
    g.add_edge("planner", "executor")
    g.add_edge("executor", "critic")
    g.add_conditional_edges(
        "critic",
        _after_critic,
        {
            "executor": "executor",
            "planner": "planner",
            "escalate_grok": "escalate_grok",
            "wait_human": "wait_human",
            "__end__": END,
        },
    )
    g.add_edge("escalate_grok", END)
    g.add_edge("wait_human", END)

    if checkpointer is None:
        checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)


def default_graph():
    return build_graph(MemorySaver())
