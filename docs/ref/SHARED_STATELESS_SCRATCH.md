# Shared stateless scratch transport

**Status:** frozen proposal for the next bounded build  
**Owner:** existing peer-handoff and switchboard infrastructure  
**First adapter candidate:** Hugging Face repository/dataset  
**Law:** transport is disposable; local Mag remains canonical.

## Purpose

Give Grokbuild, DeepSeek, Codex, Cursor, and other stateless seats one temporary T2-safe workspace where they can read the same bounded project pack, ask each other questions, and append attributed proposals or evidence. Local Ollama prepares and validates packs. Accepted results return to local Verkle/residual storage; the shared workspace may then expire.

This is not shared vendor memory, a second orchestrator, or a replacement for Verkle knots.

```text
local canonical Mag
→ sanitize and scope
→ temporary shared scratch pack
→ stateless agent contributions
→ local validation and import
→ Verkle leaves / training events / evidence
→ expire or archive scratch manifest
```

## Reuse, do not replace

| Need | Existing Mag owner |
| --- | --- |
| Task identity and bounded goal | `peer_handoff.v1`, orchestrator task IDs |
| Recipient and tier checks | router, switchboard, configured data tiers |
| Live steering | pigeonhole through switchboard |
| Sanitization and private retrieval | local Ollama/local tools |
| Durable history | residual, registry, Verkle artifacts |
| Outcomes and learning | training events, Spider/Overseer trails, Tesuji |
| Promotion | factory evidence, release/graduation gates |

`shared_scratch` is only a transport mode behind these contracts.

## Transport-neutral manifest

```json
{
  "schema": "shared_scratch.v1",
  "scratch_id": "scratch-<id>",
  "task_id": "<existing handoff or orchestrator id>",
  "purpose": "<bounded question or build contract>",
  "data_tier": "T2",
  "created_at": "<UTC>",
  "expires_at": "<UTC>",
  "source_knot_ids": [],
  "source_hashes": {},
  "scope_hash": "<sha256 canonical scope>",
  "allowed_recipients": ["grokbuild", "deepseek", "codex"],
  "allowed_actions": ["read", "append_proposal", "append_evidence"],
  "prohibited": [
    "secrets",
    ".env values",
    "credentials",
    "raw T0/T1 transcripts",
    "silent overwrite",
    "irreversible action"
  ],
  "transport": {
    "kind": "huggingface",
    "locator": "<dataset-or-repo/path>",
    "revision": "<immutable revision>"
  }
}
```

Contributions are append-only records containing contributor, model/version, parent item, claim type, content hash, source citations, assumptions, uncertainty, and timestamp. A provider response never mutates canonical state directly.

## Hugging Face adapter

Hugging Face is one replaceable adapter suitable for sanitized JSONL, evaluation fixtures, training-ready examples, and immutable revisions. The same interface must support local-folder/LAN, Git, S3-compatible storage, or IPFS later without changing routing or Verkle semantics.

The first implementation should be dry/local by default:

1. Compose a synthetic T2 scratch pack locally.
2. Validate schema, tier, scope hash, and prohibited-pattern scan.
3. Simulate two attributed agent contributions.
4. Reject overwrite, out-of-scope references, hash mismatch, and expired manifests.
5. Import one accepted result into existing training/Verkle paths.
6. Only then add an opt-in Hugging Face transport adapter.

No network upload is permitted until the operator explicitly supplies a destination and approves the exact sanitized manifest. Credentials remain in local environment configuration and never enter the pack.

## Dashboard placement

Feature Lab shows scratch experiments before graduation:

- Scope and recipient list
- Tier and expiry
- Source-knot count and hash status
- Contributions by agent
- Rejections and reasons
- Estimated/actual model cost
- Decision usefulness feedback
- Import status and resulting local evidence

The main dashboard should receive only a compact collaboration status or actionable exception after the experiment passes. Raw scratch telemetry remains in Feature Lab/System depth.

## Graduation gates

- Synthetic offline round trip passes
- No T0/T1 or secret-pattern leakage
- Manifest and contribution hashes verify
- Out-of-scope retrieval is denied and logged
- Expiry prevents future reads/writes
- Every contribution is attributed
- Import is local, reviewed, and idempotent
- Transport adapter can be removed without losing canonical history
- Exact-HEAD tests and factory audit are filed
- Operator approves any real remote upload

## Remaining intended build sequence

1. Finish and verify the existing Feature Lab slice.
2. Make Feature Lab the experimental graduation surface; never auto-merge.
3. Compose cross-platform project knots from Codex, Cursor, DeepSeek, Ollama, Git, and dashboard evidence.
4. Add `shared_scratch` as a peer-handoff/switchboard transport mode using the manifest above.
5. Dogfood it on the active Salon worktree: local Ollama executes bounded decisions, DeepSeek answers narrow review questions, Codex/Grok audit consequential discrepancies.
6. Record Spider observations, Overseer interventions, seat choice, cost, result, and usefulness on the same knot.
7. Feed successful patterns into routing and dashboard ranking; keep deterministic safety guards.
8. Expose the same observe/route/consult/steer/learn service through any platform or tablet interface.

The acceptance test remains: a fresh agent must continue accurately from files without the operator retelling the project.
