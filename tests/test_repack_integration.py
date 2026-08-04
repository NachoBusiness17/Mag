"""C2 repack integration (Run 5): long synthetic session forces AUTO-REPACK
through the REAL run_turn loop on a small-window provider (ollama 32K).

Verifies: repack fires mid-loop (trace `repack#N`), the loop RECOVERS and
continues (no crash, no budget stop), the repacked residual is live in the
history, and the final answer still lands.

Tool args ROTATE so the L3 collapse detector (5 identical calls -> hard stop)
does not flag the synthetic storm as a degenerate loop. Each tool result is a
~6K-char blob (clipped at TOOL_RESULT_CHARS) so growth crosses the ollama
threshold (~22.9K est tokens at ratio 0.85) after ~14 rounds.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mag.agent_cli as ac
from models.providers import chat_messages as real_chat


def tc(tid, n):
    return {
        "id": tid,
        "type": "function",
        "function": {
            "name": "run_python",
            "arguments": json.dumps({"code": f"print('Z' * {5900 + (n % 7) * 10})"}),
        },
    }


class StormModel:
    """Keeps returning tool calls (rotating big prints -> context grows), then final."""

    def __init__(self, rounds_before_final=18):
        self.rounds_before_final = rounds_before_final
        self.calls = 0

    def __call__(self, provider, messages, **kw):
        self.calls += 1
        if self.calls < self.rounds_before_final:
            t = tc(f"c{self.calls}", self.calls)
            return {
                "ok": True,
                "text": "",
                "tool_calls": [t],
                "message": {"role": "assistant", "content": "", "tool_calls": [t]},
            }
        return {
            "ok": True,
            "text": "final answer after synthetic storm",
            "tool_calls": [],
            "message": {"role": "assistant", "content": "final answer after synthetic storm"},
        }


def _run_storm(rounds=18):
    ac.chat_messages = StormModel(rounds_before_final=rounds)
    try:
        return ac.run_turn(
            "synthetic storm",
            provider="ollama",
            model=None,
            messages=[{"role": "system", "content": "sys"}],
        )
    finally:
        ac.chat_messages = real_chat


def test_auto_repack_fires_and_recovers_mid_loop():
    ans, messages, traces = _run_storm()

    repacks = [t for t in traces if t.startswith("repack#")]
    assert repacks, f"auto-repack never fired: {traces}"
    assert "final answer after synthetic storm" in ans, f"loop did not recover: {ans[:200]}"
    assert "stopped" not in ans.lower(), f"loop hard-stopped: {ans[:200]}"
    blob = json.dumps(messages, default=str)
    assert "auto-repack" in blob.lower(), "repacked residual missing from live history"
    print("PASS test_auto_repack_fires_and_recovers_mid_loop")
    print("  repack traces:", repacks)
    print("  ans:", ans[:80])


def test_repack_collapse_is_lean():
    """Repack drops the bloated tool chain: only post-repack tool msgs remain."""
    _, messages, _ = _run_storm()

    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    # 18-round storm unrepacked would leave 18 tool messages; repack must have
    # dropped most of the chain.
    assert len(tool_msgs) <= 8, f"tool chain not dropped by repack: {len(tool_msgs)} tool msgs"
    assert messages[0]["role"] == "system", "repacked messages lost system role"
    print("PASS test_repack_collapse_is_lean tool_msgs=", len(tool_msgs), "total_msgs=", len(messages))
