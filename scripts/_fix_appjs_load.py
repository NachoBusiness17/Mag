from pathlib import Path
import re

app = Path("dashboard/static/app.js")
t = app.read_text(encoding="utf-8")

# Drop orphan optional-chain lines (PowerShell stripped $("#id"))
lines = t.splitlines(keepends=True)
fixed = []
bad_n = 0
for line in lines:
    if re.match(r"^\s*\?\.", line):
        bad_n += 1
        continue
    fixed.append(line)
t = "".join(fixed)
print("removed orphan lines", bad_n)

if "wireDaysDesk()" not in t.replace("function wireDaysDesk()", ""):
    # call once at start of bind
    if "function bind() {" in t and "wireDaysDesk();\n" not in t:
        t = t.replace("function bind() {", "function bind() {\n  try { wireDaysDesk(); } catch (e) { console.error(e); }\n", 1)
        print("wired wireDaysDesk into bind")
else:
    print("wireDaysDesk call present")

# Ensure diary handlers also in bind if missing after orphan strip
if 'btnDiaryReload")?.addEventListener' not in t and "$(\"#btnDiaryReload\")" not in t:
    print("WARNING diary wires missing")
else:
    print("diary wires ok")

app.write_text(t, encoding="utf-8")

# syntax check with node
import subprocess
r = subprocess.run(["node", "--check", str(app)], capture_output=True, text=True)
print("node check", r.returncode, r.stderr[:500] if r.stderr else "OK")

idx = Path("dashboard/static/index.html")
it = idx.read_text(encoding="utf-8")
for name in ("app.js", "windows.js", "cli.css", "style.css", "visual.js", "board.js"):
    it = re.sub(rf"{re.escape(name)}\?v=[^\"]+", f"{name}?v=tesuji9", it)
idx.write_text(it, encoding="utf-8")
print("cache tesuji9", "app.js?v=tesuji9" in idx.read_text(encoding="utf-8"))
print("scripts", re.findall(r'src="/static/[^"]+")', idx.read_text(encoding="utf-8")))
