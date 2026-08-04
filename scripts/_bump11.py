from pathlib import Path
import re

p = Path("dashboard/static/index.html")
t = p.read_text(encoding="utf-8")
t = re.sub(r'app\.js\?v=[^"]+', "app.js?v=tesuji11", t)
t = re.sub(r'cli\.css\?v=[^"]+', "cli.css?v=tesuji11", t)
p.write_text(t, encoding="utf-8")
print("markers", "tapHoverRail" in t, "tap-canvas-wrap" in t, "tesuji11" in t)

css = Path("dashboard/static/cli.css")
block = r"""

/* === tesuji11: Days 3D — full graph + fixed right rail (no jump) === */
.days-merge {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.days-split {
  display: grid !important;
  grid-template-columns: minmax(240px, 30%) minmax(0, 1fr) !important;
  gap: 0.5rem !important;
  height: calc(100vh - 5.25rem) !important;
  min-height: 0 !important;
  overflow: hidden;
}
.days-list-col {
  overflow: auto;
  min-height: 0;
  border-right: 1px solid var(--line);
  padding-right: 0.4rem;
}
.days-graph-col {
  display: flex !important;
  flex-direction: column !important;
  min-height: 0 !important;
  min-width: 0 !important;
  overflow: hidden !important;
  gap: 0.35rem !important;
}
.days-graph-col .tap-toolbar {
  flex: 0 0 auto;
}
/* Stage: canvas | right rail — inspect no longer under the graph */
.days-tap.tap-stage,
.tap-stage.days-tap {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 280px) !important;
  grid-template-rows: 1fr !important;
  gap: 0 !important;
  overflow: hidden !important;
  border: 1px solid var(--line);
  background: #050a08;
  border-radius: 4px;
}
.tap-canvas-wrap {
  position: relative;
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  background: #050a08;
}
.tap-canvas-wrap #tapCanvas,
.days-tap #tapCanvas {
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  max-width: none !important;
  display: block !important;
  cursor: grab;
}
.tap-hover-off,
.days-tap .tap-hover {
  display: none !important;
}
.days-rail.tap-inspect,
.tap-inspect.days-rail {
  display: flex !important;
  flex-direction: column !important;
  min-height: 0 !important;
  height: 100% !important;
  max-height: none !important;
  border-left: 1px solid var(--line) !important;
  border-top: none !important;
  background: var(--panel);
  overflow: hidden !important;
  flex: none !important;
}
.rail-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.rail-hover {
  flex: 0 0 38%;
  max-height: 42%;
  border-bottom: 1px solid var(--line);
  overflow: hidden;
}
.rail-pin {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}
.rail-body.tap-inspect-body {
  flex: 1 1 auto;
  overflow: auto !important;
  min-height: 0;
  padding: 0.55rem 0.7rem !important;
  font-size: 0.85rem !important;
  line-height: 1.4 !important;
}
.rail-hint {
  margin-top: 0.35rem !important;
  font-size: 0.75rem !important;
}
.rail-actions {
  flex: 0 0 auto;
  padding: 0.45rem 0.55rem;
  border-top: 1px solid var(--line);
  gap: 0.35rem;
  margin: 0 !important;
}
.days-rail .tap-inspect-h {
  flex: 0 0 auto;
  padding: 0.4rem 0.65rem;
  font-size: 0.72rem;
}
@media (max-width: 960px) {
  .days-split {
    grid-template-columns: 1fr !important;
    height: auto !important;
    overflow: auto;
  }
  .days-tap.tap-stage {
    min-height: 420px !important;
    grid-template-columns: minmax(0, 1fr) minmax(200px, 40%) !important;
  }
}
"""
text = css.read_text(encoding="utf-8")
if "tesuji11: Days 3D" not in text:
    css.write_text(text + block, encoding="utf-8")
    print("css appended")
else:
    print("css already")
