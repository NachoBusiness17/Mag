from pathlib import Path
import subprocess

from mag.repo_readiness import repo_readiness


def _run(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_clean_tracked_repo_is_handoff_ready(tmp_path: Path):
    _run(tmp_path, "init")
    _run(tmp_path, "config", "user.email", "mag@example.invalid")
    _run(tmp_path, "config", "user.name", "Mag Test")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    _run(tmp_path, "add", "a.txt")
    _run(tmp_path, "commit", "-m", "init")
    result = repo_readiness(tmp_path)
    assert not result["handoff_ready"]
    assert result["dirty"] is False
    assert "no upstream" in " ".join(result["blockers"])


def test_dirty_repo_reports_changed_counts(tmp_path: Path):
    _run(tmp_path, "init")
    (tmp_path / "new.txt").write_text("new", encoding="utf-8")
    result = repo_readiness(tmp_path)
    assert result["dirty"] is True
    assert result["untracked"] == 1
    assert result["handoff_ready"] is False
