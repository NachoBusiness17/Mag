from pathlib import Path
import re

p = Path(__file__).resolve().parents[1] / "mag" / "story.py"
t = p.read_text(encoding="utf-8")

# Replace whole inspiration entries by name key
def swap_inspiration(text: str, old_name: str, new_name: str, new_why: str) -> str:
    # match "name": "old"... "why": "..."  within one object
    pat = re.compile(
        r'(\{\s*"name":\s*")' + re.escape(old_name) + r'("\s*,\s*"why":\s*")([^"]*)(")',
        re.M,
    )
    def repl(m):
        return m.group(1) + new_name + m.group(2) + new_why + m.group(4)
    out, n = pat.subn(repl, text)
    print(old_name, "->", n)
    return out

t = swap_inspiration(
    t,
    "Steiniger craft (structure only)",
    "Stable structure without stealing a persona",
    "You can borrow scaffolding ideas for stability without shipping someone else\u2019s AI identity as the product.",
)
t = swap_inspiration(
    t,
    "New Quixote stance",
    "Tilt at ordinary-looking capture",
    "Fight systems that look like normal help; stay practical, not a hype choir.",
)
# catch residual
t = re.sub(r"[Ss]aelis\w*", "third-party persona", t)
t = t.replace("Saelis-as-product", "someone else\u2019s AI persona as the product")
t = t.replace("strike the chord", "deep mirror analysis")
t = t.replace("Strike the chord", "Deep mirror analysis")

p.write_text(t, encoding="utf-8")
from mag.story import build_story

s = build_story(write_face=True)
print("names:", [i["name"] for i in s["inspiration"]])
blob = str(s).lower()
print("saelis?", "saelis" in blob)
print("steiniger?", "steiniger" in blob)
print("quixote?", "quixote" in blob)
