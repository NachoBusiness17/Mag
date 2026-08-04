from pathlib import Path
import re

p = Path("dashboard/static/index.html")
t = p.read_text(encoding="utf-8")
t = re.sub(r'app\.js\?v=[^"]+', "app.js?v=tesuji12", t)
t = re.sub(r'cli\.css\?v=[^"]+', "cli.css?v=tesuji12", t)
p.write_text(t, encoding="utf-8")
print("project block", "diaryProject" in t, "tesuji12", "tesuji12" in p.read_text(encoding="utf-8"))
