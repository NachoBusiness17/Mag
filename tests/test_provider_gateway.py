"""Tests for the Sovereign Provider Gateway (backend/provider_gateway.py).

Covers the operator's vision: task different API chains with jobs, agnostically
— auth gate, real provider routing (mocked), context preservation across a
chain, and unknown-provider rejection.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.provider_gateway import app, run_turn, _CONTEXTS  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _keys():
    """Fake provider keys so auth works without touching real secrets.

    Patches the reference the gateway actually holds (it imports
    `provider_keys` directly into its own namespace).
    """
    with patch("backend.provider_gateway.provider_keys", return_value=["test-key-123"]):
        _CONTEXTS.clear()
        yield


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "deepseek" in body["providers"]


def test_run_turn_auth_required():
    r = client.post("/api/v1/run_turn", json={"prompt": "hello", "provider": "deepseek"})
    assert r.status_code == 401
    assert "key" in r.json()["detail"].lower()


def test_run_turn_auth_bad_key():
    r = client.post(
        "/api/v1/run_turn",
        json={"prompt": "hello", "provider": "deepseek"},
        headers={"X-API-Key": "wrong"},
    )
    assert r.status_code == 401


def test_run_turn_success_mocked():
    with patch(
        "backend.provider_gateway.chat_messages",
        return_value={"ok": True, "text": "DeepSeek processed: hello", "model": "deepseek-v4-flash", "key_idx": 0},
    ) as cm:
        r = client.post(
            "/api/v1/run_turn",
            json={"prompt": "hello", "provider": "deepseek", "tier": "T2"},
            headers={"X-API-Key": "test-key-123"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["provider_used"] == "deepseek"
    assert "hello" in body["content"]
    assert body["error"] is None
    assert cm.call_args.kwargs["tier"] == "T2"


def test_run_turn_omitted_tier_fails_closed():
    with patch(
        "backend.provider_gateway.chat_messages",
        return_value={"ok": False, "error": "refused: tier T1 cannot use remote deepseek"},
    ) as cm:
        r = client.post(
            "/api/v1/run_turn",
            json={"prompt": "unclassified", "provider": "deepseek"},
            headers={"X-API-Key": "test-key-123"},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "error"
    assert "tier T1" in r.json()["error"]
    assert cm.call_args.kwargs["tier"] == "T1"


def test_run_turn_history_snapshot():
    """chat_messages receives the OpenAI-style history with the user last."""
    seen = []

    def fake(pid, messages, **kw):
        seen.append(list(messages))  # snapshot (run_turn mutates the same list)
        return {"ok": True, "text": "DeepSeek processed: hello", "model": "deepseek-v4-flash", "key_idx": 0}

    with patch("backend.provider_gateway.chat_messages", side_effect=fake):
        r = client.post(
            "/api/v1/run_turn",
            json={"prompt": "hello", "provider": "deepseek", "tier": "T2"},
            headers={"X-API-Key": "test-key-123"},
        )
    assert r.status_code == 200
    assert seen, "chat_messages was never called"
    msgs = seen[0]
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == "hello"


def test_run_turn_unknown_provider():
    r = client.post(
        "/api/v1/run_turn",
        json={"prompt": "x", "provider": "nope"},
        headers={"X-API-Key": "test-key-123"},
    )
    # auth gate for unknown provider: authenticate() -> False -> 401
    assert r.status_code == 401
    # run_turn itself rejects unknown providers too
    res = run_turn("x", provider="nope")
    assert res["status"] == "error"
    assert "unknown provider" in res["error"]


def test_context_preservation_across_chain():
    """Two jobs on the same context_id: the second sees the first's answer."""
    def fake_chat(pid, messages, **kw):
        # messages: [system?] user -> assistant chain
        n_user = sum(1 for m in messages if m["role"] == "user")
        return {
            "ok": True,
            "text": f"answer{n_user}",
            "model": "deepseek-v4-flash",
            "key_idx": 0,
        }

    snapshots = []

    def fake_chat(pid, messages, **kw):
        snapshots.append(list(messages))  # snapshot at call time
        n_user = sum(1 for m in messages if m["role"] == "user")
        return {
            "ok": True,
            "text": f"answer{n_user}",
            "model": "deepseek-v4-flash",
            "key_idx": 0,
        }

    with patch("backend.provider_gateway.chat_messages", side_effect=fake_chat):
        r1 = client.post(
            "/api/v1/run_turn",
            json={"prompt": "job one", "context_id": "chain-a", "provider": "deepseek", "tier": "T2"},
            headers={"X-API-Key": "test-key-123"},
        )
        r2 = client.post(
            "/api/v1/run_turn",
            json={"prompt": "job two", "context_id": "chain-a", "provider": "deepseek", "tier": "T2"},
            headers={"X-API-Key": "test-key-123"},
        )
    assert r1.json()["content"] == "answer1"
    assert r2.json()["content"] == "answer2"
    # second call's history carried the first assistant turn
    assert len(snapshots) == 2
    hist2 = snapshots[1]
    roles = [m["role"] for m in hist2]
    assert roles.count("assistant") == 1
    assert "answer1" in [m["content"] for m in hist2 if m["role"] == "assistant"]


def test_provider_failure_does_not_poison_chain():
    """A failed provider call must not leave its user turn in the chain."""
    with patch(
        "backend.provider_gateway.chat_messages",
        return_value={"ok": False, "error": "HTTP 429: rate limited"},
    ):
        res = run_turn("will fail", context_id="chain-b", provider="deepseek", tier="T2")
    assert res["status"] == "error"
    assert "429" in res["error"]
    # chain-b history: only the failed user turn was popped -> empty
    assert _CONTEXTS.get("chain-b") == [] or _CONTEXTS["chain-b"] == []
