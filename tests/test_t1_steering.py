"""T1 steering mock E2E: !pause/!continue/!escape/!steer must act MID-ROUND.

Fakes chat_messages (deterministic): each fake "model call" injects an operator
command into the steer queue before returning, simulating the operator typing
while the seat was streaming/working. Then real run_turn machinery
(apply_steer, pause gates, escape checkpoints, collapse detector) runs.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mag.agent_cli as ac


class FakeModel:
    """Returns scripted responses; injects operator commands at controlled points."""

    def __init__(self, script):
        # script: list of (inject_before_return, response_dict)
        self.script = list(script)
        self.calls = 0

    def __call__(self, provider, messages, **kw):
        self.calls += 1
        inject, resp = self.script[self.calls - 1] if self.calls <= len(self.script) else (None, {"ok": True, "text": "final", "tool_calls": [], "message": {"role": "assistant", "content": "final"}})
        if inject:
            ac._STEER_QUEUE.put(inject)  # operator typed while model was "streaming"
        return resp


def tool_call(name="read_file", args=None, tid="call_test_1"):
    return {
        "id": tid,
        "type": "function",
        "function": {"name": name, "arguments": '{"path": "memory/working.md"}' if args is None else args},
    }


def reset_state():
    ac._paused.clear()
    ac._steer_interrupt.clear()
    while not ac._STEER_QUEUE.empty():
        try:
            ac._STEER_QUEUE.get_nowait()
        except Exception:
            break


def test_pause_holds_mid_round():
    """!pause typed during model call -> pause gate holds after the tool
    executes; !continue typed 0.5s later resumes; round completes."""
    reset_state()
    script = [
        ("!pause", {"ok": True, "text": "", "tool_calls": [tool_call()], "message": {"role": "assistant", "content": "", "tool_calls": [tool_call()]}}),
        (None, {"ok": True, "text": "done after resume", "tool_calls": [], "message": {"role": "assistant", "content": "done after resume"}}),
    ]
    fake = FakeModel(script)
    ac.chat_messages = fake

    def resume_later():
        time.sleep(0.6)
        ac._STEER_QUEUE.put("!continue")

    import threading
    threading.Thread(target=resume_later, daemon=True).start()
    t0 = time.time()
    ans, messages, traces = ac.run_turn(
        "test goal", provider="fake", model=None, messages=[{"role": "system", "content": "sys"}]
    )
    elapsed = time.time() - t0
    assert "done after resume" in ans, f"round did not finish: {ans}"
    assert elapsed >= 0.5, f"pause did not hold (elapsed {elapsed:.2f}s)"
    assert fake.calls == 2, f"expected 2 model calls, got {fake.calls}"
    assert any("read_file" in t for t in traces), f"tool not executed: {traces}"
    print("PASS test_pause_holds_mid_round", f"elapsed={elapsed:.2f}s", traces)


def test_escape_aborts_round():
    """!escape typed during model call -> tool chain skipped, round aborted."""
    reset_state()
    script = [
        ("!escape", {"ok": True, "text": "", "tool_calls": [tool_call()], "message": {"role": "assistant", "content": "", "tool_calls": [tool_call()]}}),
    ]
    fake = FakeModel(script)
    ac.chat_messages = fake
    ans, messages, traces = ac.run_turn(
        "test goal", provider="fake", model=None, messages=[{"role": "system", "content": "sys"}]
    )
    assert "aborted" in ans.lower() or "escape" in ans.lower(), f"not aborted: {ans}"
    assert any("escape" in t for t in traces), f"no escape trace: {traces}"
    assert fake.calls == 1, f"model should be called once, got {fake.calls}"
    print("PASS test_escape_aborts_round", traces)


def test_steer_absorbed_next_round():
    """!steer typed during tool exec -> absorbed before the NEXT model call
    (mid-round injection, not just between user turns)."""
    reset_state()
    script = [
        ("!steer switch to writing the report", {"ok": True, "text": "", "tool_calls": [tool_call()], "message": {"role": "assistant", "content": "", "tool_calls": [tool_call()]}}),
        (None, {"ok": True, "text": "report done", "tool_calls": [], "message": {"role": "assistant", "content": "report done"}}),
    ]
    fake = FakeModel(script)
    ac.chat_messages = fake
    ans, messages, traces = ac.run_turn(
        "test goal", provider="fake", model=None, messages=[{"role": "system", "content": "sys"}]
    )
    assert "report done" in ans
    # the steer must be visible to the model call #2 -> check messages fed to fake
    fed = [c[1] for c in fake.script if c[1].get("text") == "report done"]
    joined = " ".join(str(m.get("content", "")) for m in messages if isinstance(m, dict))
    assert "switch to writing the report" in joined, f"steer not injected into messages: {joined[-400:]}"
    assert any("steer" in t for t in traces), f"no steer trace: {traces}"
    print("PASS test_steer_absorbed_next_round", traces)


def test_escape_mid_tool_loop():
    """!escape typed DURING tool execution (after 1 tool ran) -> remaining
    tools skipped, round ends cleanly."""
    reset_state()
    script = [
        (None, {"ok": True, "text": "", "tool_calls": [tool_call(tid="t1"), tool_call(tid="t2")], "message": {"role": "assistant", "content": "", "tool_calls": [tool_call(tid="t1"), tool_call(tid="t2")]}}),
    ]
    fake = FakeModel(script)
    ac.chat_messages = fake

    # operator types !escape right after the first tool starts executing
    orig_run_tool = ac._run_tool

    def run_tool_with_escape(name, args):
        out = orig_run_tool(name, args)
        ac._STEER_QUEUE.put("!escape")
        return out

    ac._run_tool = run_tool_with_escape
    try:
        ans, messages, traces = ac.run_turn(
            "test goal", provider="fake", model=None, messages=[{"role": "system", "content": "sys"}]
        )
    finally:
        ac._run_tool = orig_run_tool
    assert "aborted" in ans.lower() or "escape" in ans.lower(), f"not aborted: {ans}"
    assert any("escape" in t for t in traces), f"no escape trace: {traces}"
    print("PASS test_escape_mid_tool_loop", traces)


if __name__ == "__main__":
    test_pause_holds_mid_round()
    test_escape_aborts_round()
    test_steer_absorbed_next_round()
    test_escape_mid_tool_loop()
    print("\nALL T1 STEERING TESTS PASSED")
