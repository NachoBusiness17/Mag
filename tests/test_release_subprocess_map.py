"""Subprocess map tests for release registry."""
from mag.release_registry import build_subprocess_map, format_subprocess_text


def test_build_subprocess_map_has_analogs():
    reg = build_subprocess_map()
    assert reg.get("schema") == "mag_version_subprocess.v1"
    by_id = {r["id"]: r for r in reg.get("releases") or []}
    assert by_id["v1"]["subprocess"]["analog"] == "remote_activation_seat"
    assert by_id["v2"]["subprocess"]["analog"] == "residual_dna + modules"
    assert by_id["v3"]["subprocess"]["analog"] == "orchestrator_run"


def test_format_subprocess_text():
    text = format_subprocess_text()
    assert "v1" in text
    assert "remote_activation_seat" in text
    assert "Versions are runs" in text
