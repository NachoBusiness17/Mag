"""Container-first install artifacts exist."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docker_files_present():
    assert (ROOT / "Dockerfile").is_file()
    assert (ROOT / "docker-compose.yml").is_file()
    assert (ROOT / "scripts" / "container" / "entrypoint.sh").is_file()
    assert (ROOT / "launch_mag_container.cmd").is_file()
    assert (ROOT / "scripts" / "install.ps1").is_file()


def test_compose_binds_localhost_only():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "127.0.0.1:8765:8765" in text
    assert "cap_drop" in text
    assert "MAG_CONTAINER" in text


def test_bind_host_helper():
    from config import bind_host

    assert bind_host() == "127.0.0.1"
