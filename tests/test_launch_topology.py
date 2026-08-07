"""Regression checks for the single-owner desktop launch topology."""

import mag_launch
from mag import api_server


def test_supervisor_owns_tool_backend_and_drainer_is_opt_in(monkeypatch):
    monkeypatch.delenv("MAG_DRAINER", raising=False)
    monkeypatch.setattr(mag_launch, "_drainer_wanted", lambda: False)

    slots = {slot["name"]: slot for slot in mag_launch.build_slots()}

    assert slots["backend"]["wanted"] is True
    backend_cmd = slots["backend"]["cmd"]
    assert "-m" in backend_cmd and "backend.server" in backend_cmd
    assert slots["drainer"]["wanted"] is False
    # Integral lab is supervised (watch+companion); dashboard separate for UI
    assert slots["lab"]["wanted"] is True
    assert "lab" in slots["lab"]["cmd"]
    assert "--no-dashboard" in slots["lab"]["cmd"]
    assert slots["dashboard"]["wanted"] is True


def test_authenticated_gateway_does_not_claim_tool_backend_port():
    assert api_server.DEFAULT_PORT == 8001


def test_browser_env_allowlist_gate():
    from mag.browser_env import is_host_allowed, load_config, status

    st = status()
    assert st.get("schema") == "mag_browser_env.v1"
    assert st.get("ok") is True
    # Default off — no free browsing until operator enables + installs driver
    assert st.get("enabled") is False
    assert is_host_allowed("https://chat.openai.com/") is False
    cfg = load_config()
    cfg["enabled"] = True
    assert is_host_allowed("https://chat.openai.com/c/x", cfg) is True
    assert is_host_allowed("https://evil.example/", cfg) is False
