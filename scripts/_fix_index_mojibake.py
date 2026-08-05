from pathlib import Path

p = Path("dashboard/static/index.html")
t = p.read_text(encoding="utf-8")
repl = {
    "\u00e2\u20ac\u201d": "\u2014",  # â€" -> em dash (common mojibake)
    "\u00e2\u20ac\u201c": "\u2014",
    "\u00e2\u80\u93\u00b6": "\u25b6",  # â–¶
    "\u00e2\u80\u93\u00a1": "\u25a1",  # â–¡
    "\u00c3\u2014": "\u00d7",  # Ã—
    "\u00e2\u20ac\u00a6": "\u2026",  # â€¦
}
# also literal broken sequences if file has them
literal = {
    "â€"": "\u2014",
    "â–¶": "\u25b6",
    "â–¡": "\u25a1",
    "Ã—": "\u00d7",
    "â€¦": "\u2026",
}
for a, b in {**repl, **literal}.items():
    t = t.replace(a, b)
p.write_text(t, encoding="utf-8")
print("done")
