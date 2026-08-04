"""Seat crash-guard LIVE test (Run 1 refine): one-shot crash -> nonzero exit + log.

Exercises the REAL run_agent one-shot path with injected failures:
  - run_turn raises mid-turn (provider-style crash) -> do_turn inner guard
    recovers and logs stage=do_turn.
  - save_session raises during persist (post-turn persistence crash) ->
    propagates out of do_turn -> one_shot outer guard -> _log_seat_crash
    stage=one_shot + return 1 (nonzero exit).

Exit-code propagation: run_agent returns 1; main_argv sys.exit(main_argv()) -> 1.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mag.agent_cli as ac

MARK = "INJECTED-ONESHOT-CRASH"


def _log_text() -> str:
    p = ac.ROOT / "logs" / "seat_crashes.log"
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def _install_boom():
    real_run_turn = ac.run_turn
    real_save = ac.save_session

    def boom_run_turn(*a, **k):
        raise RuntimeError(f"{MARK}-MIDTURN")

    def boom_save(*a, **k):
        raise RuntimeError(f"{MARK}-PERSIST")

    ac.run_turn = boom_run_turn
    ac.save_session = boom_save
    return real_run_turn, real_save


def _restore(real_run_turn, real_save):
    ac.run_turn = real_run_turn
    ac.save_session = real_save


def test_one_shot_crash_nonzero_exit_and_logged():
    before = _log_text()
    real_run_turn, real_save = _install_boom()
    try:
        rc = ac.run_agent(provider="fake", model=None, one_shot="say hi")
    finally:
        _restore(real_run_turn, real_save)

    assert rc == 1, f"expected nonzero exit for one-shot crash, got {rc}"
    new = _log_text()[len(before):]
    assert "stage=do_turn" in new, f"inner guard (do_turn) not logged: {new[-400:]}"
    assert "stage=one_shot" in new, f"outer guard (one_shot) not logged: {new[-400:]}"
    assert MARK in new, f"crash marker missing from log: {new[-400:]}"
    print("PASS test_one_shot_crash_nonzero_exit_and_logged rc=", rc)


def test_main_argv_propagates_nonzero_exit():
    """CLI entry: sys.exit(main_argv()) -> run_agent's return 1 becomes exit 1."""
    real_run_turn, real_save = _install_boom()
    try:
        rc = ac.main_argv(["-q", "say hi", "--provider", "fake"])
    finally:
        _restore(real_run_turn, real_save)
    assert rc == 1, f"main_argv should return 1, got {rc}"
    print("PASS test_main_argv_propagates_nonzero_exit rc=", rc)
