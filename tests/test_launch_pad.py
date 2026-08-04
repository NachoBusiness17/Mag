"""Launch pad for fresh installs / republic entry."""

from mag.launch_pad import build_launch_pad


def test_launch_pad_framework_on_empty():
    lp = build_launch_pad(n_sessions=0, ship="PROVISIONAL")
    assert lp["show"] is True
    assert lp["framework_ready"] is True
    assert lp["personal_beads_empty"] is True
    assert any(f["id"] == "activation" and f["ok"] for f in lp["framework"])
    assert len(lp["core_ops"]) >= 3


def test_launch_pad_hidden_when_beads_ok():
    lp = build_launch_pad(n_sessions=5, ship="OK")
    assert lp["show"] is False
