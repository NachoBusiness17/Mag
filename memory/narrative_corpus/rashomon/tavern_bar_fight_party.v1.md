# Rashomon seed — tavern bar fight (full party)

**Schema:** `mag_rashomon_seed.v1`  
**Event id:** `tavern_bar_fight_party`  
**Place:** The Guttered Lantern (hub)  
**Use:** multi-perspective train + salon dogfood — **not** literal Campbell/Jung dump  

## Engine truth (FILE — Sancho’s ledger)

- Time: evening, common room full  
- Parties present: fighter, wizard, rogue, + barkeep, stranger in corner  
- Trigger: argument over **who left the loft window unlatched** (keep smoke rumor related or not — disputed)  
- Physical: one mug broken, one chair tipped, no deaths  
- Fighter shoved rogue; wizard cast a harmless light cantrip that panicked a patron  
- Barkeep called “out” once; stranger never stood up  
- HP: fighter −0, rogue −1 bruise, wizard −0, others unharmed  
- Flags after: `bar_brawl_tonight`, `barkeep_annoyed`  

Models must not contradict engine_truth when role is **engine** or **rules clerk**.

---

## Perspective: fighter

I only stopped the thief from lying. Window was their job. Mug was already cracked. Light wasn’t my idea. I’d do it again — quieter next time if the mage keeps their fireworks.

## Perspective: wizard

I de-escalated with illumination. The fighter escalates with mass. The rogue invents chores. The unlatched window is a metaphor for porous security at the keep. Also I paid for the mug. Probably.

## Perspective: rogue

I was *upstairs* inventoring the snore-dust. Window was latched when I left. Fighter needs a villain. Wizard needs a thesis. Barkeep needs coin. I need fewer witnesses.

## Perspective: barkeep

They broke a mug. They scared the regulars. Keep politics does not pour ale. Next time: outside. I don’t care who left which window in which story.

## Perspective: stranger (corner)

I saw the light first. Then the shove. Then three different windows in three mouths. I finished my broth. I still don’t know if the keep smokes black.

## Perspective: engine_truth

(see ledger above — short, checkable, boring on purpose)

---

## Train labels (future)

```json
{
  "event_id": "tavern_bar_fight_party",
  "perspectives": ["fighter", "wizard", "rogue", "barkeep", "stranger", "engine_truth"],
  "task": "given perspective_id, rewrite beat without inventing HP/deaths",
  "hard_negative": "claim someone died",
  "salon_use": "guest options: believe fighter / check loft / pay mug / leave"
}
```

## Craft rails (silent)

- Unreliable voice = character; **engine_truth** = Sancho  
- Le Guin-clean when rendering one voice  
- Attention framing: each voice *wants* you to side with them (fiction only)  
- Hub return: fight ends, still in tavern unless engine moves you  
