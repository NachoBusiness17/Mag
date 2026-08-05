# FEATURE — Bridgefy P2P / Mesh / Broadcast transmission modes

**Commitment:** `feat-bridgefy-transmission-001`  
**Source:** `mine/raw/mesh_comm/bridgefy/sdk-android` README  
**Parent:** `docs/templates/FEATURE_COMPOSE.md`

## Identify

| Field | Value |
|-------|-------|
| name | typed_transmission_modes |
| foreign form | `TransmissionMode.P2P` · `Mesh(receiver)` · `Broadcast` + propagation profiles |
| invariant | IF undifferentiated send THEN flood or missed offline delivery |

## Evaluate

| | |
|--|--|
| same | pigeonhole knot = directed; switchboard `steer_drop` = tier-bounded slice |
| differ | Bridgefy is SDK for apps; Mag is harness — steal **enum**, not SDK dep |
| Mag slot | `mag/pigeonhole.py` · switchboard drop kinds |

## Steal

| Bridgefy mode | Mag analog (draft) |
|---------------|-------------------|
| P2P | Direct steer to one `task_id` |
| Mesh | Multi-hop via enrolled relay peers (v5, willing) |
| Broadcast | **reject** for Mag ops — spider/nervous only, not goals |
| Propagation profiles (dense/sparse) | spider stall thresholds · autorun pause in crowded queue |

## Enhance

- Broadcast forbidden for BUILD goals (plan theater amplifier)  
- Mesh requires `willing_participation` gate in `configs/mesh_comm_repos.yaml`  

## Compose

Pairs with Bitchat TTL/dedup → loop detector `mesh_flood` (v4 draft).

## Measure

overlap **wire** into pigeonhole/switchboard docs — no Bridgefy AAR in Mag core.

## Promote

Defer code until G4 interconnect spec. Spore only.
