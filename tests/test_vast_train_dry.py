import hashlib
import json

from mag import vast_train


def _bundle(tmp_path):
    export = tmp_path / "train.jsonl"
    row = {"schema": "mag_training_event.v1", "tier_max": "T2", "pattern": "route_decision"}
    export.write_text(json.dumps(row) + "\n", encoding="utf-8")
    manifest = {
        "schema": "training_export_manifest.v1",
        "source_schema": "mag_training_event.v1",
        "tier_max": "T2",
        "n_exported": 1,
        "sha256": hashlib.sha256(export.read_bytes()).hexdigest(),
    }
    export.with_suffix(".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return export


def test_dry_run_validates_and_estimates_without_launch(tmp_path):
    out = vast_train.dry_run(_bundle(tmp_path), max_hours=2)
    assert out["ok"] is True
    assert out["dry"] is True
    assert out["launched"] is False
    assert out["validation"]["rows"] == 1
    assert out["estimate"]["estimated_max_usd"] <= out["estimate"]["spend_cap_usd"]


def test_tampered_export_is_rejected(tmp_path):
    export = _bundle(tmp_path)
    export.write_text(export.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    out = vast_train.dry_run(export)
    assert out["ok"] is False
    assert "manifest sha256 mismatch" in out["validation"]["errors"]


def test_unknown_model_and_hour_cap_are_rejected(tmp_path):
    export = _bundle(tmp_path)
    assert vast_train.dry_run(export, base_model="missing")["ok"] is False
    assert vast_train.dry_run(export, max_hours=999)["ok"] is False
