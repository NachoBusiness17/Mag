"""Dashboard bind policy — localhost default, explicit LAN opt-in."""
from __future__ import annotations

import pytest

from config import (
    LAB_BIND_PATH,
    bind_exposure,
    bind_host,
    clear_lab_bind,
    read_lab_bind,
    record_lab_bind,
    resolve_bind_host,
)


@pytest.fixture(autouse=True)
def _clean_bind(tmp_path, monkeypatch):
    bind_file = tmp_path / "lab_bind.json"
    monkeypatch.setattr("config.LAB_BIND_PATH", bind_file)
    yield
    clear_lab_bind()


def test_bind_host_default_localhost(monkeypatch):
    monkeypatch.delenv("MAG_BIND_HOST", raising=False)
    monkeypatch.delenv("MAG_LAN", raising=False)
    monkeypatch.delenv("MAG_CONTAINER", raising=False)
    assert bind_host() == "127.0.0.1"


def test_resolve_ignores_mag_bind_host_without_lan(monkeypatch, capsys):
    monkeypatch.setenv("MAG_BIND_HOST", "0.0.0.0")
    monkeypatch.delenv("MAG_LAN", raising=False)
    monkeypatch.delenv("MAG_CONTAINER", raising=False)
    assert resolve_bind_host() == "127.0.0.1"
    assert "ignoring MAG_BIND_HOST" in capsys.readouterr().out


def test_resolve_lan_flag_records_pref(monkeypatch):
    monkeypatch.delenv("MAG_CONTAINER", raising=False)
    host = resolve_bind_host(lan=True, port=8765)
    assert host == "0.0.0.0"
    pref = read_lab_bind()
    assert pref.get("lan") is True
    info = bind_exposure(host=host, port=8765)
    assert info["mode"] == "lan"
    assert info["warning"]


def test_resolve_local_only_clears_pref(monkeypatch):
    record_lab_bind(lan=True, host="0.0.0.0", port=8765)
    host = resolve_bind_host(local_only=True)
    assert host == "127.0.0.1"
    assert read_lab_bind() == {}


def test_resolve_restores_saved_lan_on_restart(monkeypatch):
    monkeypatch.delenv("MAG_CONTAINER", raising=False)
    record_lab_bind(lan=True, host="0.0.0.0", port=8765)
    assert resolve_bind_host() == "0.0.0.0"


def test_refuse_host_override_without_lan(monkeypatch, capsys):
    monkeypatch.delenv("MAG_CONTAINER", raising=False)
    host = resolve_bind_host(host_override="0.0.0.0")
    assert host == "127.0.0.1"
    assert "refused 0.0.0.0" in capsys.readouterr().out


def test_container_honors_mag_bind_host(monkeypatch):
    monkeypatch.setenv("MAG_CONTAINER", "1")
    monkeypatch.setenv("MAG_BIND_HOST", "0.0.0.0")
    assert bind_host() == "0.0.0.0"
    assert resolve_bind_host() == "0.0.0.0"
