from pathlib import Path

from mag.conductor_eval import load_suite, run_eval


def test_frozen_conductor_suite_is_complete():
    suite = load_suite()
    assert suite["schema"] == "conductor_eval_suite.v1"
    assert suite["threshold"] == 1.0
    assert len(suite["cases"]) >= 10


def test_conductor_eval_passes_without_writing():
    report = run_eval(write=False)
    assert report["ok"] is True
    assert report["score"] == 1.0
    assert report["passed"] == report["total"]


def test_conductor_eval_files_evidence(tmp_path, monkeypatch):
    import mag.conductor_eval as evaluator

    monkeypatch.setattr(evaluator, "EVAL_DIR", tmp_path)
    report = evaluator.run_eval(write=True)
    assert report["ok"] is True
    assert (tmp_path / "latest.json").is_file()
    assert Path(tmp_path / "latest.json").read_text(encoding="utf-8").find('"score": 1.0') > 0
