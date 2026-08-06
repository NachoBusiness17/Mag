"""Cast receiver — read-only LAN pulse without desk exposure."""
from __future__ import annotations

import json
import threading
from http.client import HTTPConnection

import pytest

from mag import cast_server as cs


def test_render_cast_page_has_headline():
    html_out = cs.render_cast_page({"headline": "Test pulse", "status": "ok", "events": ["one"]})
    assert "Test pulse" in html_out
    assert "http-equiv=\"refresh\"" in html_out


def test_cast_allowed_routes_only():
    assert "/api/v1/display" in cs._ALLOWED
    assert "/api/v1/remote/intent" in cs._ALLOWED
    assert "/api/v1/desk-dialogue" not in cs._ALLOWED


def test_cast_server_read_only_localhost():
    port = 18766
    host = "127.0.0.1"
    thread = threading.Thread(target=lambda: cs.run(host=host, port=port), daemon=True)
    thread.start()

    import time

    for _ in range(30):
        try:
            conn = HTTPConnection(host, port, timeout=1)
            conn.request("GET", "/")
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            conn.close()
            assert resp.status == 200
            assert "Mag Cast" in body
            break
        except Exception:
            time.sleep(0.1)
    else:
        pytest.skip("cast server did not start in time")

    conn = HTTPConnection(host, port, timeout=5)
    conn.request("POST", "/api/v1/voice/turn", body=b"{}", headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    conn.close()
    assert resp.status == 400

    conn = HTTPConnection(host, port, timeout=1)
    conn.request("POST", "/api/v1/desk-dialogue", body=b"{}", headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    conn.close()
    assert resp.status == 405
