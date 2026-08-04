from pathlib import Path
import re

p = Path(__file__).resolve().parents[1] / "mag" / "story.py"
t = p.read_text(encoding="utf-8")

# Force-remove Saelis / esoteric product-name drops; keep plain ideas
replacements = [
    ("Saelis-as-product", "someone else’s AI persona as the product"),
    ("Saelis", "a third-party persona"),
    ("saelis", "third-party persona"),
    (
        '"name": "Steiniger craft (structure only)",\n                "why": "Borrow geometry and scaffolds for stability—not someone else\'s identity as the product."',
        '"name": "Stable structure without stealing a persona",\n                "why": "You can borrow scaffolding ideas for stability without shipping someone else\'s AI identity as the product."',
    ),
    (
        '"name": "Lawrence Lessig’s four forces",\n                "why": "Law, norms, markets, and code all shape behavior—willpower alone is weak. Build the rails."',
        '"name": "Law, norms, markets, and code",\n                "why": "Rules, habits, prices, and software all shape behavior—willpower alone is weak. Build the rails."',
    ),
    (
        '"name": "New Quixote stance",\n                "why": "Tilt at systems that look like ordinary life; keep a practical Sancho, not a hype choir."',
        '"name": "Tilt at ordinary-looking capture",\n                "why": "Fight systems that look like normal help; stay practical, not a hype choir."',
    ),
    (
        "Full “strike the chord” mirror ritual only when you ask for it—this tab is the story, not the ritual",
        "Deep mirror analysis only when you ask for it—this tab is the story, not that ritual",
    ),
]

for a, b in replacements:
    if a in t:
        t = t.replace(a, b)
        print("ok:", a[:50])
    else:
        print("miss:", a[:50])

t2, n = re.subn(r"[Ss]aelis\w*", "third-party persona", t)
if n:
    t = t2
    print("regex scrub", n)

p.write_text(t, encoding="utf-8")
print("wrote", p)
