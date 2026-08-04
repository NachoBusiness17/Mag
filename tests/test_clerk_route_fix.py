"""Clerk-route fix tests: no silent grok default on non-JSON clerk replies.

Routing only — `_run_local` is mocked so tests stay fast and offline.
"""
from __future__ import annotations

from unittest.mock import patch

from mag.route import route_goal

LOCAL_OK = {"action": "ask", "ok": True, "answer": "mock", "used_llm": False}


def _clerk_echo(role, system, user, temperature=0.1):
    """Simulate gemma:2b echoing the instruction instead of JSON."""
    return 'Route only. JSON: {"lane":"local|grok|wait","reason":"short"}'


def test_valid_json_local_lane():
    with patch("mag.route.chat", return_value='{"lane":"local","reason":"short"}'):
        with patch("mag.route._run_local", return_value=LOCAL_OK):
            out = route_goal("design a distributed ledger for the republic")
    assert out["lane"] == "local"
    assert out["reason"] == "short"
    assert out["ok"] is True


def test_echoed_instruction_ambiguous_goes_grok_but_explicit():
    # no heuristic keyword -> clerk echoes instruction (non-JSON) -> grok via observable fallback
    with patch("mag.route.chat", _clerk_echo):
        out = route_goal("design a distributed ledger for the republic")
    assert out["lane"] == "grok"
    assert out["reason"] == "heuristic:fallback"
    assert out["clerk_raw"] is not None


def test_invalid_lane_string_rejected_not_trusted():
    # clerk returns invalid lane -> rejected; ambiguous goal -> grok with explicit fallback reason
    with patch("mag.route.chat", return_value='{"lane":"nonsense","reason":"x"}'):
        out = route_goal("design a distributed ledger for the republic")
    assert out["lane"] == "grok"
    assert "fallback" in out["reason"]


def test_heuristic_recall_still_local_without_clerk():
    # 'recall' hits local_recall heuristic before any clerk call -> local, fast, no clerk_raw
    with patch("mag.route.chat", _clerk_echo):
        with patch("mag.route._run_local", return_value=LOCAL_OK):
            out = route_goal("what was i doing? recall my session")
    assert out["lane"] == "local"
    assert out["reason"] == "heuristic:local_recall"
    assert out["clerk_raw"] is None  # clerk never called


def test_clerk_raw_kept_for_audit():
    # ambiguous goal -> clerk called; echoed text kept in output for auditing
    with patch("mag.route.chat", _clerk_echo):
        out = route_goal("ponder the nature of ledgers tonight")
    assert out["clerk_raw"] is not None
    assert "Route only" in out["clerk_raw"]
