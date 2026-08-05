# FEATURE — Bitchat dual-transport MessageRouter

**Commitment:** `feat-bitchat-dual-transport-001`  
**Source:** `mine/raw/mesh_comm/permissionlesstech/bitchat` · WHITEPAPER.md  
**Research:** field-steal 20260805T125129Z · research-pack 20260805T125145Z  
**Parent:** `docs/templates/FEATURE_COMPOSE.md`

## Identify

| Field | Value |
|-------|-------|
| name | dual_transport_router |
| foreign form | `MessageRouter` prefers BLE mesh → Nostr → courier store-and-forward |
| invariant | IF single-transport-only THEN partitioned/offline users lose coordination fidelity |

## Evaluate

| | |
|--|--|
| same | Mag already has LAN `:8765` + hub fallback (DeepSeek/GSTD) — same *shape* |
| differ | Bitchat is radio mesh; Mag is disk + switchboard — steal **routing policy**, not BLE stack |
| capture risk | low if contracts only |
| local cost | $0 — conductor overlay research |

## Steal

**Contract:** Ordered fallback chain with explicit probe at each hop:

```text
live_local → mesh_transport (v5 opt-in) → hub_seat (GSTD/API) → defer + FILE
```

**Maps to:** `mag/conductor.py` phase + `configs/seat_playbook.yaml` transport_chain (draft).

## Enhance (Mag invariants)

- T0/T1 never on mesh without operator L3 enroll  
- pigeonhole `steer_drop` for directed traffic; no broadcast flood (Bitchat TTL/dedup → loop_audit pattern)  
- Artifact > transcript — courier = trail on disk, not chat scroll  

## Compose

Reinforces: switchboard tier drops · GSTD as hub seat · ILAP routing matrix.

**Cancels failure mode:** “smart model picks transport by vibes” → conductor declares chain.

## Measure

- routing_smoke green for scut/local goals  
- eval-ilap-002 research_dive filed  
- overlap: **wire** — extend conductor, no new module  

## Promote

**Candidate:** playbook line + `training_patterns.yaml` `transport_fallback` (v4 draft).  
**Not auto-promote.**
