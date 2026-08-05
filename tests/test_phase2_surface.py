"""Phase 2 — seat feed + preferences."""
from __future__ import annotations

from mag.preferences import drainer_enabled, set_drainer
from mag.seat_feed import unified_seat_feed


def test_unified_seat_feed_shape():
    res = unified_seat_feed(limit=5)
    assert res.get("ok") is True
    assert isinstance(res.get("entries"), list)


def test_drainer_pref_toggle(monkeypatch):
    monkeypatch.delenv("MAG_DRAINER", raising=False)
    set_drainer(False)
    assert drainer_enabled() is False
    set_drainer(True)
    assert drainer_enabled() is True
    set_drainer(False)
