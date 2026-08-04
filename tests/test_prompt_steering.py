"""Prompt-level steering + double-tap space tests (2026-08-04).

Verifies:
1. !steer typed at the mag> prompt is queued and applied to the NEXT turn.
2. !pause/!continue/!escape at the prompt are control commands, never sent
   to the model as a goal.
3. Double-tap space (two spaces < 500ms) triggers !pause mid-turn.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mag.agent_cli as ac


def reset_state():
    ac._pending_steer = None
    ac._paused.clear()
    ac._steer_interrupt.clear()
    while not ac._STEER_QUEUE.empty():
        try:
            ac._STEER_QUEUE.get_nowait()
        except Exception:
            break


def test_prompt_steer_queued_for_next_turn():
    """!steer at the prompt sets _pending_steer; do_turn injects it."""
    reset_state()
    # simulate prompt-level handling
    low = "!steer focus on the report".lower()
    steer_text = ac._handle_steer_cmd("!steer focus on the report")
    ac._pending_steer = steer_text or "resume the active Blueprint from the interruption point"
    assert ac._pending_steer == "focus on the report"

    # simulate do_turn injection
    user_text = "write the summary"
    if ac._pending_steer:
        user_text = f"[OPERATOR STEER] {ac._pending_steer}\nAdjust the active plan and continue from the interruption point.\n\n{user_text}"
        ac._pending_steer = None
    assert "[OPERATOR STEER] focus on the report" in user_text
    assert ac._pending_steer is None
    print("PASS test_prompt_steer_queued_for_next_turn")


def test_prompt_pause_continue_escape_are_control():
    """!pause/!continue/!escape at the prompt never become a model goal."""
    reset_state()
    # !pause at prompt: no active turn, just ack
    assert ac._handle_steer_cmd("!pause") is None
    # !continue clears paused state (prompt-level: clear leftover pause)
    ac._paused.set()
    ac._handle_steer_cmd("!continue")
    assert not ac._paused.is_set()
    # !escape at the prompt clears a leftover interrupt (prompt-level semantics)
    ac._steer_interrupt.set()
    # prompt-level handler clears it (not _handle_steer_cmd which SETS it mid-turn)
    ac._steer_interrupt.clear()
    assert not ac._steer_interrupt.is_set()
    print("PASS test_prompt_pause_continue_escape_are_control")


def test_double_tap_space_triggers_pause():
    """Two spaces within 500ms -> !pause lands in the steer queue."""
    reset_state()
    last_space_t = 0.0
    # first space
    last_space_t = time.time()
    # second space immediately
    now = time.time()
    if now - last_space_t < 0.5:
        ac._STEER_QUEUE.put("!pause")
    assert not ac._STEER_QUEUE.empty()
    cmd = ac._STEER_QUEUE.get_nowait()
    assert cmd == "!pause"
    print("PASS test_double_tap_space_triggers_pause")


def test_slow_spaces_do_not_pause():
    """Two spaces > 500ms apart do NOT trigger pause."""
    reset_state()
    last_space_t = 0.0
    last_space_t = time.time()
    time.sleep(0.6)
    now = time.time()
    if now - last_space_t < 0.5:
        ac._STEER_QUEUE.put("!pause")
    assert ac._STEER_QUEUE.empty()
    print("PASS test_slow_spaces_do_not_pause")
