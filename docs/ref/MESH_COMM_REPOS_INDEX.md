# Mesh / offline comm — local research index

**Commitment:** `mesh-comm-repos-index-001`  
**v5 plan:** `docs/ref/MAG_v5_MESH_FOREST.md` — **piped** (research + ILAP now; implement v5+)  
**Local clones:** `mine/raw/mesh_comm/` (gitignored — refresh with `scripts/pull_mesh_comm_repos.sh`)  
**Manifest:** `configs/mesh_comm_repos.yaml`  
**Purpose:** ILAP research agent + steal protocol — offline/mesh **transport contracts** for mycelial republic; **not** a v3 dependency.

**Honesty:** Upstream apps are **products with their own licenses**. Mag steals **ops grammar** (multi-hop, dual transport, willing relay) into switchboard / pigeonhole / deferred G4 interconnect — never app cosplay or silent device enlistment.

---

## Repos (10 targets)

| ID | Local path | Upstream | License | One-line |
|----|------------|----------|---------|----------|
| **bitchat** | `mine/raw/mesh_comm/permissionlesstech/bitchat` | [permissionlesstech/bitchat](https://github.com/permissionlesstech/bitchat) | Unlicense | BLE mesh + Nostr dual transport; multi-hop (7) |
| **bitchat-android** | `…/permissionlesstech/bitchat-android` | [bitchat-android](https://github.com/permissionlesstech/bitchat-android) | GPL-3.0 | Cross-platform binary protocol; Wi-Fi Aware |
| **georelays** | `…/permissionlesstech/georelays` | [georelays](https://github.com/permissionlesstech/georelays) | check upstream | Nostr relay geography map |
| **bridgefy-android** | `…/bridgefy/sdk-android` | [bridgefy/sdk-android](https://github.com/bridgefy/sdk-android) | check upstream | Embeddable BLE mesh SDK — P2P/Mesh/Broadcast |
| **bridgefy-ios** | `…/bridgefy/sdk-ios` | [bridgefy/sdk-ios](https://github.com/bridgefy/sdk-ios) | check upstream | iOS mesh SDK |
| **bridgefy-flutter** | `…/bridgefy/bridgefy_flutter` | [bridgefy_flutter](https://github.com/bridgefy/bridgefy_flutter) | check upstream | Flutter wrapper |
| **briar** | `…/briar/briar` | [briar/briar](https://github.com/briar/briar) · [GitLab primary](https://code.briarproject.org/briar/briar) | GPL-3.0 | Tor + BT/Wi-Fi sync; no central server |
| **briar-mailbox** | `…/briar/briar-mailbox` | [briar-mailbox](https://github.com/briar/briar-mailbox) | AGPL-3.0 | Optional mailbox when device offline |
| **briar-desktop** | `…/briar/briar-desktop` | [briar-desktop](https://github.com/briar/briar-desktop) | GPL-3.0 | Desktop peer |
| **briar-onionwrapper** | `…/briar/onionwrapper` | [onionwrapper](https://github.com/briar/onionwrapper) | GPL-3.0 | Tor transport library |

---

## Research tags (ILAP / spore catalog)

| Tag | Steal into Mag slot |
|-----|---------------------|
| `mesh_ble` | Deferred G4 transport research — not Mag DNA |
| `dual_transport` | conductor route: local mesh → hub fallback (like bitchat BLE→Nostr) |
| `multi_hop` | switchboard tier drops along knot — not broadcast |
| `no_central_server` | fork equality / no throne registry |
| `willing_participation` | opt-in edge node (GSTD + household mesh) |
| `mailbox_bridge` | optional relay seat — operator runs mailbox, not Mag default |
| `sdk_embeddable` | household apps wrap Bridgefy-style SDK later |

---

## Mag relevance (future — v5 mesh forest)

| Foreign pattern | Mag slot (when wired) |
|-----------------|------------------------|
| Bitchat dual transport | `route.v2` fallback chain: LAN → mesh → hub → defer |
| Bridgefy P2P/Mesh/Broadcast | pigeonhole transmission modes (steer not flood) |
| Briar sync-without-server | beads on disk + sync when paths exist (zeitgeist) |
| Briar mailbox | optional **willing** relay peer — like GSTD edge, not identity |
| Georelays | research only — Nostr != Mag DNA |

See `MAG_v5_MESH_FOREST.md` for **eventual service** vision (self-governing mesh agent, MIT/permissive forest seat).

---

## Refresh clones

```bash
chmod +x scripts/pull_mesh_comm_repos.sh
./scripts/pull_mesh_comm_repos.sh
```

Windows:

```cmd
scripts\pull_mesh_comm_repos.cmd
```

Override dest: `MAG_MESH_DEST=/path/to/clones ./scripts/pull_mesh_comm_repos.sh`

Shallow clone (`--depth 1`); re-run to `git pull` existing dirs.

---

## ILAP scout commands

```powershell
./scripts/mesh_comm_ilap_run.sh   # full pipeline — pull, steal, pack, improve, smoke, events
```

Manual slices:

```powershell
./scripts/pull_mesh_comm_repos.sh
mag.cmd improve --once
mag.cmd research-pack --ask "Bitchat dual transport routing contract" --url "https://github.com/permissionlesstech/bitchat"
python main.py field-steal --root mine/raw/mesh_comm/permissionlesstech/bitchat --max-files 30
```

Spores (filed): `docs/ref/spores/mesh/` · ILAP: `docs/ref/proposals/ILAP-mesh-steal-001.md`

---

## Do not commit

- `mine/raw/mesh_comm/**` — full upstream trees stay local only  
- AGPL/GPL source **inside Mag repo** — reference only on disk  
- Never auto-enlist user devices in mesh without L3 consent  

---

## Related

| Doc | Role |
|-----|------|
| `MAG_v5_MESH_FOREST.md` | v5 pipe track — mesh + willing participation |
| `MAG_v5_GSTD_FOREST.md` | DePIN compute seat (parallel track) |
| `MAG_ILAP_PROTOCOL.md` | Research before BUILD |
| `memory_verkle_map.md` | Field → lattice map |
