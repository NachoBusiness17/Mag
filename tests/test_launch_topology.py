"""Regression checks for the single-owner desktop launch topology."""

import mag_launch
from mag import api_server


def test_supervisor_owns_tool_backend_and_drainer_is_opt_in(monkeypatch):
    monkeypatch.delenv("MAG_DRAINER", raising=False)

    slots = {slot["name"]: slot for slot in mag_launch.build_slots()}

    assert slots["backend"]["wanted"] is True
    assert slots["backend"]["cmd"][-2:] == ["-m", "backend.server"]
    assert slots["drainer"]["wanted"] is False


def test_authenticated_gateway_does_not_claim_tool_backend_port():
    assert api_server.DEFAULT_PORT == 8001
