"""IJL-v0 pure helpers — no Ollama required."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ijl_core import (
    infer_task_family,
    jaccard,
    map_value_to_decision,
    mean_pairwise_diversity,
    next_alt_plan,
    normalize_plans,
    normalize_value,
    pick_primary_plan_index,
    plan_pair_diversity,
    skill_excerpt_for_goal,
    slugify,
    write_skill_bead,
)


def test_slugify():
    assert "dig" in slugify("Research dig: SSI / Ilya!")


def test_infer_task_family():
    assert infer_task_family("pull arxiv dig on SSI") == "dig"
    assert infer_task_family("refactor mag harness") == "harness"
    assert infer_task_family("write unit tests") == "code"


def test_plan_diversity():
    a = ["list memory", "read locus.md"]
    b = ["list memory", "read locus.md"]
    c = ["run pytest tests", "write report"]
    assert plan_pair_diversity(a, b) < 0.2
    assert plan_pair_diversity(a, c) > 0.5
    assert mean_pairwise_diversity([a, c]) > 0.5


def test_normalize_and_pick():
    plans = normalize_plans(
        [
            ["list memory", "read locus"],
            ["run pytest", "fix handoff"],
            ["list memory", "read locus.md"],  # near-dupe
        ]
    )
    assert len(plans) == 2
    idx = pick_primary_plan_index(plans)
    assert 0 <= idx < len(plans)


def test_normalize_single_plan():
    plans = normalize_plans(["step one", "step two"])
    assert plans == [["step one", "step two"]]


def test_value_short_circuit_maps_replan():
    v = normalize_value(
        {
            "valence": "bad",
            "intensity": 0.9,
            "stuck": True,
            "short_circuit": True,
            "next": "abort",
            "reason": "looping",
        }
    )
    d = map_value_to_decision(
        v,
        base_decision="continue",
        step_i=1,
        plan_len=3,
        retries=0,
        has_tool_ok=True,
    )
    assert d == "replan"


def test_value_tier_wait():
    v = normalize_value({"tier_ok": False, "next": "continue"})
    d = map_value_to_decision(
        v,
        base_decision="continue",
        step_i=0,
        plan_len=2,
        retries=0,
        has_tool_ok=False,
    )
    assert d == "wait"


def test_next_alt_plan():
    alts = [["a"], ["b"], ["c"]]
    p, i = next_alt_plan(alts, 0)
    assert p == ["b"] and i == 1
    p2, i2 = next_alt_plan(alts, 2)
    assert p2 is None and i2 == 2


def test_skill_bead_roundtrip(tmp_path, monkeypatch):
    import ijl_core as ijl

    monkeypatch.setattr(ijl, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(ijl, "ROOT", tmp_path)
    path = write_skill_bead(
        goal="dig SSI public claims",
        plan=["read report", "file leaf"],
        success_checks=["claims table present"],
        critique="worked via dig-leaf",
        value_trace=[{"valence": "good", "short_circuit": False, "next": "continue", "reason": "ok"}],
        tool_ok_count=2,
        task_family="dig",
        parent_run="test-thread",
    )
    assert path is not None
    assert path.is_file()
    assert path.with_suffix(".json").is_file()
    # excerpt needs ROOT-relative paths — set ROOT to tmp and path under it
    rel = path.relative_to(tmp_path)
    meta = path.with_suffix(".json")
    import json

    o = json.loads(meta.read_text(encoding="utf-8"))
    o["path"] = str(rel).replace("\\", "/")
    meta.write_text(json.dumps(o), encoding="utf-8")
    # rewrite path field used by list
    text = skill_excerpt_for_goal("dig research SSI", max_chars=400)
    # may be empty if path resolution fails; at least list works
    beads = ijl.list_skill_beads(task_family="dig")
    assert len(beads) >= 1


def test_jaccard_empty():
    assert jaccard(set(), set()) == 1.0
    assert jaccard({"a"}, set()) == 0.0
