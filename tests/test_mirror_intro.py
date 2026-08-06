"""Mirror first-run tour assets are present in the dashboard shell."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "dashboard" / "static" / "index.html"
APP_JS = ROOT / "dashboard" / "static" / "app.js"
CSS = ROOT / "dashboard" / "static" / "cli.css"


def test_mirror_guide_markup_in_index():
    html = INDEX.read_text(encoding="utf-8")
    assert 'id="mirrorGuide"' in html
    assert 'id="mirrorGuideTitle"' in html
    assert 'id="btnMirrorReplay"' in html
    assert "mirror-intro-v1" in CSS.read_text(encoding="utf-8")


def test_mirror_guide_logic_in_app_js():
    js = APP_JS.read_text(encoding="utf-8")
    assert "MIRROR_INTRO_KEY" in js
    assert "MIRROR_GUIDE_STEPS" in js
    assert "maybeStartMirrorGuide" in js
    assert "Hi — I'm your Mirror" in js
