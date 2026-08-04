from pathlib import Path

p = Path(__file__).resolve().parents[1] / "mag" / "story.py"
text = p.read_text(encoding="utf-8")
start = text.index("_JOURNEY: list[dict[str, Any]] = [")
new = r'''_JOURNEY: list[dict[str, Any]] = [
    {
        "phase": "1",
        "title": "Something felt off about the default path",
        "prose": (
            "The normal stack—platforms that speak for you, AI that remembers for a fee, "
            "news that feels like a story engine—stopped looking neutral. A second path "
            "showed up: keep your own notes, use models as tools, don’t build a church."
        ),
        "beats": [
            "Public writing stayed yours to quote as-written later",
            "Early mirror instruments as craft, not costume",
            "A standing no to “the model is the truth”",
        ],
    },
    {
        "phase": "2",
        "title": "Two houses with a clear wall",
        "prose": (
            "We split the work: a private office (Mag) for day-to-day filing and tools, "
            "and a public project (Mycelial Republic) for shared rules and practice data. "
            "The wall is simple: private life doesn’t get checked into the public repo."
        ),
        "beats": [
            "Written constitution and agency rules (you approve the big moves)",
            "Mag day beads and end-of-day filing",
            "A short daily card: find → file → load",
        ],
    },
    {
        "phase": "3",
        "title": "Rented computers taught a hard lesson",
        "prose": (
            "A rented GPU could answer fast while research quietly went off the rails—"
            "thin sources, polluted queues, fake confidence. We kept a portable bag of what "
            "mattered and left the rent behind. Compute is a tool; memory stays home."
        ),
        "beats": [
            "Tunnel into the rent for inference only",
            "Wrote down what failed and what to gate next time",
            "Stopped treating “the machine answered” as “we know”",
        ],
    },
    {
        "phase": "4",
        "title": "Briefings, health checks, honest multi-AI",
        "prose": (
            "We taught the office to hand every model a short briefing pack, to show system "
            "health at a glance, and to let several workers report differences against a frozen "
            "base—not invent a shared brain in chat."
        ),
        "beats": [
            "context-pack and agent preambles",
            "base + drift saves with automated tests",
            "Review helper scripts and coordination docs in plain reach",
        ],
    },
    {
        "phase": "5",
        "title": "The real hard work is still soil",
        "prose": (
            "The enemy is not “missing another tab.” It’s honest practice density: annotate "
            "what matters, run self-tests with logs, only claim big training milestones when "
            "the data is real. Pretty office ≠ finished mirror."
        ),
        "beats": [
            "Boot-soil annotate path from exports you already have",
            "Self-tests and vector maps with evidence",
            "Weight training only if the archive and count are real",
            "Multi-person forest only after one healthy office",
        ],
    },
    {
        "phase": "6",
        "title": "Return with a toolbox, not a throne",
        "prose": (
            "What we carry back is portable: files, a tip of the chain, configs, a constitution "
            "others can fork. The Story tab points at those files. Charisma is optional; "
            "filing is not."
        ),
        "beats": [
            "Move-house bags",
            "Office + diary + story as three views of one life",
            "No official king of the network",
        ],
    },
]
'''
p.write_text(text[:start] + new, encoding="utf-8")
print("ok", start)
