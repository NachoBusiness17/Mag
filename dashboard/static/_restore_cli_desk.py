"""Restore interactive CLI desk from clear-UI index backup."""
from __future__ import annotations

import re
from pathlib import Path

static = Path(__file__).resolve().parent
bak = static / "index.clear-ui.html"
cur = static / "index.html"
src = (bak if bak.exists() else cur).read_text(encoding="utf-8")

if not bak.exists() and "cli-dock" not in src:
    bak.write_text(src, encoding="utf-8")
    print("backed up ->", bak.name)
elif bak.exists():
    src = bak.read_text(encoding="utf-8")
    print("source:", bak.name)


def extract_balanced(pid: str) -> str:
    m = re.search(rf'<(section|div)\s+id="{re.escape(pid)}"[^>]*>', src)
    if not m:
        raise SystemExit(f"missing {pid}")
    tag = m.group(1)
    start = m.end()
    i = start
    depth = 1
    open_re = re.compile(rf"<{tag}\b[^>]*>", re.I)
    close_re = re.compile(rf"</{tag}>", re.I)
    while i < len(src) and depth:
        om = open_re.search(src, i)
        cm = close_re.search(src, i)
        if not cm:
            break
        if om and om.start() < cm.start():
            depth += 1
            i = om.end()
        else:
            depth -= 1
            if depth == 0:
                return src[start : cm.start()].strip()
            i = cm.end()
    raise SystemExit(f"unbalanced {pid}")


titles = {
    "home": "MAP // HOME",
    "chat": "TTY // CHAT",
    "sessions": "BEADS // DAYS",
    "board": "BOARD // SCRAPS",
    "operate": "BRIEF // PASTE",
    "detail": "BEAD // DETAIL",
    "visual": "MAP // VISUAL",
    "tapestry": "MAP // 3D",
    "flow": "LEDGER // FLOW",
    "orchestrate": "SEATS // MODELS",
    "verkle": "CHAIN // TIP",
    "ingest": "INGEST // CAT",
}

dock_icons = {
    "home": ("⌂", "MAP"),
    "chat": (">_", "TTY"),
    "sessions": ("◉", "DAY"),
    "board": ("≡", "BRD"),
    "operate": ("☰", "BRF"),
    "detail": ("▣", "DET"),
    "visual": ("◈", "VIS"),
    "tapestry": ("⬡", "3D"),
    "flow": ("↕", "FLW"),
    "orchestrate": ("⚙", "MOD"),
    "verkle": ("◎", "TIP"),
    "ingest": ("↓", "ING"),
}

order = [
    "home",
    "chat",
    "sessions",
    "board",
    "operate",
    "detail",
    "visual",
    "tapestry",
    "flow",
    "orchestrate",
    "verkle",
    "ingest",
]

panels = {name: extract_balanced(f"panel-{name}") for name in order}
for name, body in panels.items():
    print(f"  {name}: {len(body)} chars")


def win_html(name: str, body: str) -> str:
    title = titles[name]
    focused = " focused" if name == "home" else ""
    active = " active" if name == "home" else ""
    return f"""
    <div class="win{focused}" data-win="{name}" id="win-{name}">
      <div class="win-titlebar">
        <span class="win-title">▶ {title}</span>
        <span class="win-ctrls">
          <button type="button" class="win-min" title="minimize">_</button>
          <button type="button" class="win-max" title="maximize">□</button>
          <button type="button" class="win-close" title="close">×</button>
        </span>
      </div>
      <div class="win-body">
        <section id="panel-{name}" class="panel{active}">
{body}
        </section>
      </div>
      <div class="win-resize" title="resize"></div>
    </div>"""


dock_lines = ['  <nav class="cli-dock" aria-label="windows">']
for name in order:
    ico, lab = dock_icons[name]
    on = " on" if name == "home" else ""
    dock_lines.append(
        f'    <button type="button" class="dock-btn{on}" data-win="{name}" '
        f'title="{titles[name]}"><span class="ico">{ico}</span><span>{lab}</span></button>'
    )
dock_lines.append("  </nav>")

win_lines = ['  <div class="desk" id="desk">']
for name in order:
    win_lines.append(win_html(name, panels[name]))
win_lines.append("  </div>")

legacy = """
  <!-- legacy ids for app.js -->
  <span id="shipBadge" class="hidden"></span>
  <span id="magOsStrip" class="hidden"></span>
  <span id="magOsVer" class="hidden"></span>
  <span id="magOsProv" class="hidden"></span>
  <span id="magOsChips" class="hidden"></span>
  <span id="magOsPhoenix" class="hidden"></span>
  <span id="magOsCardPanel" class="hidden"></span>
  <span id="magOsCardBody" class="hidden"></span>
  <span id="btnOsCard" class="hidden"></span>
  <span id="btnAdvanced" class="hidden"></span>
  <span id="advMenu" class="hidden"></span>
  <span id="healthBanner" class="hidden"></span>
  <span id="footRoot" class="hidden"></span>
  <span id="boardNote" class="hidden"></span>
  <span id="btnBoardRefresh" class="hidden"></span>
  <span id="btnCatchUpBoard" class="hidden"></span>
  <span id="boardDrawer" class="hidden"></span>
  <span id="vmapAscii" class="hidden"></span>
"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MAG // CLI DESK</title>
  <link rel="stylesheet" href="/static/style.css?v=cli3" />
  <link rel="stylesheet" href="/static/cli.css?v=cli3" />
  <script type="importmap">
  {{
    "imports": {{
      "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
      "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
    }}
  }}
  </script>
</head>
<body class="cli">
  <div class="scanlines" aria-hidden="true"></div>
  <div class="vignette" aria-hidden="true"></div>
  <header class="cli-bar top">
    <div class="brand">
      <span class="mark">MAG</span>
      <div>
        <h1>sovereign desk</h1>
        <p class="sub">FIND · FILE · LOAD · residual DNA · pack-first</p>
      </div>
    </div>
    <div class="cli-prompt">mag@local<span class="blink">_</span></div>
    <div class="actions">
      <span class="ship-badge" id="homeShip" title="Ship">…</span>
      <span class="health-pill" id="healthPill" title="Health">…</span>
      <button type="button" class="btn ghost" id="btnCatchUp">catch-up</button>
      <button type="button" class="btn ghost" id="btnRefresh">sync</button>
    </div>
  </header>
{chr(10).join(dock_lines)}
{chr(10).join(win_lines)}
{legacy}
  <script src="/static/visual.js?v=cli3"></script>
  <script src="/static/board.js?v=cli3"></script>
  <script src="/static/windows.js?v=cli3"></script>
  <script src="/static/app.js?v=cli3"></script>
</body>
</html>
"""

out = static / "index.html"
out.write_text(html, encoding="utf-8")
print("OK", out, "bytes", out.stat().st_size)
