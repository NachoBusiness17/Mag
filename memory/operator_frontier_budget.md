# Grok / frontier budget (operator ranked 2026-08-06)

Order of work: **4 purge → 2 token-chain → 1 local-default agent → 3 commit → 5 promote ≤3 → 6 Grok rare**.

## Rule for Grok TUI (this seat)
- Max **one** judgment turn per stuck gate.
- LOAD pack + goal only. No warehouse tour.
- FILE residual after decision.
- Never DeepSeek tool-loop from Grok chat for scut — use `main.py token-chain` or `agent --provider ollama`.

## DeepSeek
- Default **off** for agent/orchestrator (ollama default as of this policy).
- Use only: frozen `[build]` contracts, or `token-chain` planner (short plan JSON), or explicit `--provider deepseek` + T2.

## Observe
- Queue: `python main.py orchestrator queue status`
- Improve: `python main.py improve --status`
- Chain: `memory/runs/token_chain/latest.json`
