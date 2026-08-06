from mag.verkle_artifact import build_agent_knot, verify_leaf


def test_build_agent_knot_from_real_file():
    packet = build_agent_knot("019f4d15-dee6-76d3-9e1f-cc5dff56720d")
    assert packet["ok"] is True
    assert packet["schema"] == "mag.verkle-knot/v1"
    assert packet["identity"]["title"] == "new worktree"
    assert packet["meaning"]["operator_intent"]
    assert packet["evidence"]["verified"] is True
    assert packet["evidence"]["knot"].endswith(".knot.json")


def test_verify_leaf_rejects_mutation():
    packet = build_agent_knot("019f4d15-dee6-76d3-9e1f-cc5dff56720d")
    assert packet["evidence"]["verified"] is True
    assert verify_leaf({"leaf_hash": "0" * 64, "session_id": "changed"}) is False
