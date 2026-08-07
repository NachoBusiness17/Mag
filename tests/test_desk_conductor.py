"""Desk conductor v3 — local percolator, hot-swap, fallback."""

from __future__ import annotations

from pathlib import Path


from mag import desk_conductor as dc





def test_recommend_wake_remote(monkeypatch):
    monkeypatch.setattr("mag.desk_dialogue.DIALOGUE_LOG", Path("nonexistent-dialogue-log.jsonl"))
    monkeypatch.setattr(
        "mag.desk_overseer.measure_context_pressure",
        lambda: {"intervene": False},
    )
    action = dc.recommend_action({"wake_pending": True, "remote_asleep": False, "local_wake_pending": False})

    assert action == "wake_remote"





def test_recommend_wake_local(monkeypatch):
    monkeypatch.setattr("mag.desk_dialogue.DIALOGUE_LOG", Path("nonexistent-dialogue-log.jsonl"))
    monkeypatch.setattr(
        "mag.desk_overseer.measure_context_pressure",
        lambda: {"intervene": False},
    )
    action = dc.recommend_action({"local_wake_pending": True})

    assert action == "wake_local"





def test_conductor_glance_shape():

    g = dc.conductor_glance()

    assert g["ok"] is True

    assert g["schema"] == dc.SCHEMA

    assert g["schema"] == "mag_desk_conductor.v4"

    assert "next_action" in g

    assert "cursor" in g

    assert "health_headline" in g

    assert "scratch_tail" in g

    assert "conductor_model" in g

    assert "conductor_backend" in g





def test_conductor_model_from_lanes():

    model = dc.conductor_model()

    assert model

    assert dc.conductor_backend() in ("local", "deepseek", "auto")





def test_parse_conductor_response():

    raw = """### Advisory

Local owes a canvas edit.



### Scratch update

Goal: chess smoke. Local to move e4.



### Wake note

Local — play e4 on canvas under ### Local · move.



### Canvas edit

none"""

    parsed = dc._parse_conductor_response(raw)

    assert "Local owes" in parsed["advisory"]

    assert "chess smoke" in parsed["scratch_update"]

    assert "e4" in parsed["wake_note"]

    assert parsed["canvas_edit"] == "none"





def test_fallback_plan_wake_remote():

    plan = dc._fallback_plan(

        action="wake_remote",

        operator_note="chess smoke",

        target="remote",

        fidelity={"last_peer_message": "e4 please"},

    )

    assert plan["ok"] is True

    assert plan["backend"] == "rule"

    assert "canvas edit" in plan["wake_note"].lower()





def test_build_seat_fidelity_local():

    fid = dc.build_seat_fidelity("local")

    assert fid["seat"] == "local"

    assert fid["peer"] == "remote"

    assert "local_constraints" in fid





def test_compose_wake_payload_includes_fidelity():

    fid = dc.build_seat_fidelity("remote")

    payload = dc._compose_wake_payload(

        seat="remote",

        wake_note="Respond to Local's last edit.",

        fidelity=fid,

        operator_note="Run chess handoff smoke.",

    )

    assert "Conductor wake" in payload

    assert "Run chess handoff" in payload

    assert "Protocol" in payload





def test_apply_scratch_update_skips_hold():

    assert dc.apply_scratch_update("hold") is None

    assert dc.apply_scratch_update("") is None


