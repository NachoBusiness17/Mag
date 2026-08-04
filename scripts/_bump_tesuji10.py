from pathlib import Path
import re

p = Path("dashboard/static/index.html")
t = p.read_text(encoding="utf-8")
t = re.sub(r"app\.js\?v=[^\"]+", "app.js?v=tesuji10", t)
p.write_text(t, encoding="utf-8")
print("cache", "tesuji10" in p.read_text(encoding="utf-8"))

from dashboard.rest import dispatch

print("v1", dispatch("GET", "/api/v1/diary", None)[0])
print("legacy", dispatch("GET", "/api/diary", None)[0])
print("n", dispatch("GET", "/api/v1/diary", None)[1].get("n_entries"))
