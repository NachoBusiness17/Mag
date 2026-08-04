"""Lattice harvest gates — normalize URLs, grounding, queue gate. No Ollama."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.lattice_loop import normalize_url, should_enqueue_proposed
from mag.research_pack import answer_grounded_in_pack, score_fidelity


def test_normalize_url_strips_backtick_and_junk():
    # trailing markdown junk stripped → clean URL kept
    assert (
        normalize_url("https://nsarchive.gwu.edu/nukevault/ebb285/`")
        == "https://nsarchive.gwu.edu/nukevault/ebb285/"
    )
    assert (
        normalize_url("https://www.franklinreport.com/`")
        == "https://www.franklinreport.com/"
    )
    # backtick mid-url → reject
    assert normalize_url("https://evil.com/`path") is None
    assert normalize_url("https://example.com/x") is None
    assert normalize_url("https://www.parlament.com/en/document/x") is None
    assert normalize_url("not-a-url") is None
    assert normalize_url("https://en.wikipedia.org/wiki/Marc_Dutroux") is not None


def test_grounding_wrong_page_like_url8():
    """Nuclear vault excerpt must not count as grounded for unrelated case prose."""
    pack = {
        "sources": [
            {
                "url": "https://nsarchive.gwu.edu/nukevault/ebb285/",
                "ok": True,
                "chars": 31263,
                "excerpt": (
                    "Candid Interviews with Former Soviet Officials Reveal U.S. "
                    "Strategic Intelligence Failure Over Decades Nuclear Vault "
                    "Home Index to Postings Special Collection Key Documents on "
                    "Nuclear weapons policy Brezhnev Grechko command post exercise "
                    "strategic triad ICBM cold war deterrence archival materials"
                ),
            }
        ]
    }
    dig = (
        "The five-step containment pattern covers McMartin, Finders, Franklin, "
        "Dutroux and Epstein. Official narrative is moral panic. Dissent claims "
        "institutional protection loops. Source: https://nsarchive.gwu.edu/nukevault/ebb285/"
    )
    g = answer_grounded_in_pack(dig, pack, min_chars=500, min_token_hits=3)
    # applicable with rich body; case prose should not bind strongly
    assert g["applicable"] is True
    # may get a few accidental hits; require ungrounded under score_fidelity
    fid = score_fidelity(dig, {**pack, "success_criteria": ["Obey LAW — not courtroom proof."]})
    assert fid.get("ungrounded") is True or g.get("grounded") is False


def test_grounding_with_quote_pass():
    excerpt = (
        "Candid Interviews with Former Soviet Officials Reveal U.S. "
        "Strategic Intelligence Failure Over Decades Nuclear Vault archival "
        "materials on Brezhnev command post exercise and strategic triad ICBMs. "
        "The collection republishes primary documents from the late Cold War "
        "period including force posture studies and leadership assessments that "
        "historians use when reconstructing deterrence debates and intelligence "
        "failures across successive administrations and general staff cultures."
    )
    assert len(excerpt) >= 200
    pack = {
        "sources": [
            {
                "url": "https://nsarchive.gwu.edu/nukevault/ebb285/",
                "ok": True,
                "chars": max(4000, len(excerpt)),
                "excerpt": excerpt,
            }
        ],
        "success_criteria": ["Cite sources"],
    }
    dig = (
        f'The page states: "{excerpt[:90]}" — multi-frame hold only; residual open. '
        "Not courtroom proof. Official archival framing vs later historiography. "
        "Keywords from source body: Brezhnev command post exercise strategic triad "
        "ICBMs deterrence debates intelligence failures general staff."
    )
    g = answer_grounded_in_pack(dig, pack, min_chars=200)
    assert g["applicable"] is True
    assert g["grounded"] is True
    fid = score_fidelity(dig, pack)
    assert fid.get("ungrounded") is False


def test_queue_gate_blocks_ungrounded():
    proposed = [
        "https://www.good-source.org/doc",
        "https://nsarchive.gwu.edu/nukevault/ebb285/`",
        "https://www.parlament.com/x",
    ]
    out = should_enqueue_proposed(
        proposed=proposed,
        fidelity={"ungrounded": True, "recommend": "elevate_or_retry"},
        pack={"sources": [{"ok": True, "chars": 8000}]},
    )
    assert out == []


def test_queue_gate_normalizes_when_hold():
    proposed = [
        "https://www.cia.gov/library/readingroom/docs/x.pdf",
        "https://bad.example.com/y",
        "https://www.parlament.com/z",
    ]
    out = should_enqueue_proposed(
        proposed=proposed,
        fidelity={
            "ungrounded": False,
            "recommend": "hold",
            "grounding": {"applicable": True, "grounded": True},
        },
        pack={"sources": [{"ok": True, "chars": 8000}]},
    )
    assert out == ["https://www.cia.gov/library/readingroom/docs/x.pdf"]


def test_thin_fetch_without_honesty_ungrounded():
    pack = {
        "sources": [
            {
                "url": "https://en.wikipedia.org/wiki/Marc_Dutroux",
                "ok": False,
                "chars": 141,
                "status_code": 403,
                "excerpt": "",
            }
        ],
        "success_criteria": ["Obey LAW — not courtroom proof."],
    }
    dig = (
        "Dutroux exemplifies institutional protection. Official narrative is "
        "incompetence. Dissent claims five-step loop. Evidence from the page."
    )
    fid = score_fidelity(dig, pack)
    assert fid.get("ungrounded") is True
