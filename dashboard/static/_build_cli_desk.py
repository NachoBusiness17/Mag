"""One-shot: wrap Mag dashboard panels in CLI floating windows + verkle home map."""
from __future__ import annotations

import re
from pathlib import Path

html_path = Path(__file__).with_name("index.html")
text = html_path.read_text(encoding="utf-8")

if "cli.css" not in text:
    text = text.replace(
        '<link rel="stylesheet" href="/static/style.css" />',
        '<link rel="stylesheet" href="/static/style.css" />\n'
        '  <link rel="stylesheet" href="/static/cli.css" />',
    )

text = text.replace("<title>Mag · Resource Harness</title>", "<title>MAG // CLI DESK</title>")
text = text.replace("<title>Mag · Resource Harness</title>", "<title>MAG // CLI DESK</title>")

panels: dict[str, str] = {}
for m in re.finditer(
    r'<section id="panel-([a-z]+)" class="panel[^"]*"[^>]*>(.*?)</section>',
    text,
    flags=re.S,
):
    panels[m.group(1)] = m.group(2)

print("panels:", sorted(panels.keys()))

titles = {
    "home": "MAP // VERKLE",
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

home_body = r"""
      <div class="vmap" id="vmap">
        <div class="vmap-head">
          <div>
            <h2 class="vmap-title">Verkle structure map</h2>
            <p class="vmap-sub" id="homePath">TIP → BEAD → EDGES → LOAD</p>
            <div class="home-zg" id="homeZg"></div>
          </div>
          <div class="os-hero-actions home-hero-right">
            <span class="ship-big" id="homeShip" title="Ship badge">…</span>
            <button type="button" class="btn ghost" id="btnHomeRefresh">sync</button>
            <button type="button" class="btn" id="btnHomeChat">tty</button>
          </div>
        </div>
        <div class="phoenix-banner hidden" id="homePhoenix" role="status"></div>
        <div class="stats" id="homeStats"></div>
        <pre class="vmap-ascii" id="vmapAscii" aria-hidden="true"></pre>
        <div class="vmap-tree" id="vmapTree"></div>
        <div class="hidden" aria-hidden="true">
          <h3 id="homeBeadTitle"></h3>
          <p id="homeBeadMeta"></p>
          <p id="homeBeadBlurb"></p>
          <ul id="homeBeadBullets"></ul>
          <ul id="homeProvList"></ul>
          <p id="homeTip"></p>
          <p id="homeTipMeta"></p>
          <p id="homeEcon"></p>
          <ul id="homeSys"></ul>
          <ul id="homeVerify"></ul>
          <span id="homeVerifyScore"></span>
          <div id="homeVerifyCard"></div>
          <ul id="homeLoops"></ul>
          <ul id="homeNext"></ul>
          <ul id="homeBonds"></ul>
        </div>
        <div class="vmap-actions">
          <button type="button" class="btn ghost" id="btnHomeDays">beads</button>
          <button type="button" class="btn ghost" id="btnHomeVisual">visual</button>
          <button type="button" class="btn ghost" id="btnHomeVerify">verify</button>
        </div>
      </div>
"""
panels["home"] = home_body

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


def win_html(name: str, body: str) -> str:
    title = titles.get(name, name.upper())
    active = " active" if name == "home" else ""
    focused = " focused" if name == "home" else ""
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
        <section id="panel-{name}" class="panel{active}">{body}
        </section>
      </div>
      <div class="win-resize" title="resize"></div>
    </div>"""


dock_lines = ['  <nav class="cli-dock" aria-label="windows">']
for name in order:
    ico, lab = dock_icons.get(name, ("·", name[:3].upper()))
    on = " on" if name == "home" else ""
    dock_lines.append(
        f'    <button type="button" class="dock-btn{on}" data-win="{name}" '
        f'title="{titles.get(name, name)}">'
        f'<span class="ico">{ico}</span><span>{lab}</span></button>'
    )
dock_lines.append("  </nav>")

wins = ['  <div class="desk" id="desk">']
for name in order:
    if name not in panels:
        print("WARN missing panel", name)
        continue
    wins.append(win_html(name, panels[name]))
wins.append("  </div>")

header = """
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
      <span class="ship-badge" id="shipBadge" title="Ship">…</span>
      <span class="health-pill" id="healthPill" title="Health">…</span>
      <button type="button" class="btn ghost" id="btnCatchUp">catch-up</button>
      <button type="button" class="btn ghost" id="btnRefresh">sync</button>
    </div>
  </header>
  <div class="health-banner" id="healthBanner" hidden></div>
  <div class="mag-os-strip hidden" id="magOsStrip">
    <div class="mag-os-head">
      <span class="mag-os-ver" id="magOsVer">Mag OS v2</span>
      <span class="mag-os-prov" id="magOsProv">…</span>
      <button type="button" class="btn ghost small" id="btnOsCard">Card</button>
    </div>
    <div class="mag-os-chips" id="magOsChips"></div>
    <div class="mag-os-phoenix" id="magOsPhoenix" hidden></div>
  </div>
  <div class="mag-os-card-panel hidden" id="magOsCardPanel"><pre class="pre" id="magOsCardBody"></pre></div>
"""

scripts_m = re.search(r"(  <script src=[\s\S]*?)</body>", text)
if not scripts_m:
    raise SystemExit("no scripts block")
scripts = scripts_m.group(1)
if "windows.js" not in scripts:
    scripts = scripts.replace(
        '<script src="/static/app.js"></script>',
        '<script src="/static/windows.js"></script>\n  <script src="/static/app.js"></script>',
    )

new_body = (
    header
    + "\n".join(dock_lines)
    + "\n"
    + "\n".join(wins)
    + "\n"
    + scripts
    + "\n</body>"
)

new_html = re.sub(r"<body>[\s\S]*?</body>", new_body, text, count=1)
# also handle body class already set
if new_html == text:
    new_html = re.sub(r"<body[^>]*>[\s\S]*?</body>", new_body, text, count=1)

html_path.write_text(new_html, encoding="utf-8")
print("OK", html_path, "size", html_path.stat().st_size)
