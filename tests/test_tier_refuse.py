"""Constitutional tier refusal at the lowest remote-provider boundary."""
from __future__ import annotations

import urllib.request

import pytest

from models.providers import chat_provider


@pytest.mark.parametrize("tier", ["T0", "T1"])
def test_remote_provider_refuses_private_before_network(monkeypatch, tier):
    called = False

    def forbidden_network(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be reached for private tiers")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    out = chat_provider("deepseek", "system", "private", tier=tier)

    assert out.get("ok") is False
    assert "cannot use remote" in str(out.get("error"))
    assert called is False


def test_remote_provider_omitted_tier_fails_closed(monkeypatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("network must not be reached when tier is omitted")
        ),
    )

    out = chat_provider("deepseek", "system", "unclassified")

    assert out.get("ok") is False
    assert "tier T1" in str(out.get("error"))
