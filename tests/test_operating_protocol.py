from mag.operating_protocol import build_envelope, normalize_surface


def test_surface_aliases_do_not_change_protocol():
    assert normalize_surface("web") == "dashboard"
    assert normalize_surface("phone") == "tablet"
    rows = [build_envelope("show status", source=s) for s in ("codex", "dashboard", "tablet", "cli", "cursor", "grok")]
    assert {r["policy"]["id"] for r in rows} == {"personal-router-dungeon-master.v1"}
    assert all(r["policy"]["platform_agnostic"] for r in rows)
    assert len({tuple(r["policy"]["stages"]) for r in rows}) == 1


def test_frozen_build_defaults_to_cheap_implementation_seat():
    row = build_envelope(
        "[build] execute frozen queue/handoff/BUILD-v3-deepseek-proof.md exactly",
        source="codex",
    )
    assert row["ok"]
    assert row["execution"]["implementation_default"] == "deepseek"
    assert row["execution"]["architect"] == "personal_router"
    assert row["dungeon_master"]["role"] == "summoned_frontier_adviser"
    assert row["routing_economics"]["accounting_unit"] == "verified_leaf"
    assert "full transcript" in row["routing_economics"]["context_policy"]


def test_unfrozen_build_is_blocked_on_every_surface():
    for surface in ("codex", "dashboard", "tablet", "api"):
        row = build_envelope("[build] implement a new feature", source=surface)
        assert not row["ok"]
        assert row["execution"]["status"] == "blocked"
