# Mag economy goal

**Commitment:** `goal-fidelity-min-tokens-001`

## Strive for

| Maximize | Minimize |
|----------|----------|
| Fidelity of message (truth, cites, residual) | Tokens spent (local + remote) |
| Reuse of packs/briefs/beads | Repetition of work already filed |
| Local L0 answers | Grok TUI / remote for scut |
| One clean next move | Plan inflation / map recitation |

## How we measure

- **Local est. tokens** — what Ollama actually burned (chars/4)
- **Counterfactual TUI tokens** — if the same ask had been sent to Grok with a naive full-dump (live + long history)
- **Saved** = counterfactual − local (running total)

Dashboard Chat header shows the running count. Hitting green = Mag is doing its job.
