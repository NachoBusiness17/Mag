"""One-shot: seed Mag .env from sovereign-mirror-scaffold XAI key if present."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path.home() / "Documents/projects/worktrees/sovereign-mirror-scaffold/.env"
DST = ROOT / ".env"


def main() -> int:
    vals: dict[str, str] = {}
    if SRC.is_file():
        raw = SRC.read_text(encoding="utf-8-sig")  # strip BOM
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip().lstrip("\ufeff")] = v.strip().strip('"').strip("'")

    # preserve existing Mag .env values
    if DST.is_file():
        for line in DST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if v and k not in vals:
                vals[k] = v
            elif v and k in vals and not vals[k]:
                vals[k] = v

    xai = vals.get("XAI_API_KEY") or vals.get("GROK_API_KEY") or ""
    model = vals.get("XAI_MODEL") or "grok-4"

    def g(k: str) -> str:
        return vals.get(k) or ""

    lines = [
        "# Mag provider secrets — never commit this file",
        "# Fill empty keys; restart Mag lab after edits.",
        "",
        f"XAI_API_KEY={xai}",
        f"XAI_MODEL={model}",
        f"GROK_API_KEY={g('GROK_API_KEY')}",
        "",
        f"OPENROUTER_API_KEY={g('OPENROUTER_API_KEY')}",
        f"OPENAI_API_KEY={g('OPENAI_API_KEY')}",
        f"ANTHROPIC_API_KEY={g('ANTHROPIC_API_KEY')}",
        f"GROQ_API_KEY={g('GROQ_API_KEY')}",
        f"DEEPSEEK_API_KEY={g('DEEPSEEK_API_KEY')}",
        f"GEMINI_API_KEY={g('GEMINI_API_KEY')}",
        f"GOOGLE_API_KEY={g('GOOGLE_API_KEY')}",
        f"TOGETHER_API_KEY={g('TOGETHER_API_KEY')}",
        "",
    ]
    DST.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {DST}")
    print(f"XAI_API_KEY: {'configured' if xai else 'MISSING'} (len={len(xai)})")
    for k in (
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "DEEPSEEK_API_KEY",
        "GEMINI_API_KEY",
        "TOGETHER_API_KEY",
    ):
        print(f"{k}: {'configured' if g(k) else 'empty — paste into .env'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
