# Skybound: Veil of Worlds — Claude Design Build Prompt

Copy everything below this line into Claude Design.

---

Build a playable, single-page web game called **Skybound: Veil of Worlds** — an Afrofuturist airship exploration RPG. Mobile-first, touch-friendly, dark and luminous. Everything runs client-side; save to localStorage.

## Tone & Visual Style

Afrofuturist sky-mythology. Deep indigo night-sky background (#0a0f24), luminous teal and gold accents, biome cells that glow like stained glass. Typography clean and modern with generous spacing. The mood is wonder with an undercurrent of loss — a sky full of erased history being slowly remembered. No stock fantasy clichés: this is Black diasporic sci-fi, ancestral memory as technology.

## Core Loop

Fly an airship across a procedurally generated sky grid → discover cells → Survey → Decode them for lore → trigger encounters (combat, discovery, NPC, mythic) → make quest choices with faction consequences → earn Aether Coins → upgrade the ship → unlock higher sky layers → reconstruct the erased history of the sky.

## World Generation

- 16×16 grid, seeded (show the seed; same seed = same world).
- Three noise passes: density (island placement), elevation (sky layer), corruption (danger).
- **7 biomes**: TradeWinds (safe, commerce), AncestorFields (memory, calm), StormRift (fast currents, dangerous), ImperialCorridor (expensive to cross, patrolled), CelestialRuin (salvage + lore), VoidAnomaly (endgame, reality-unstable), Uncharted (unknown).
- **Weather per cell**: Clear ×1.0, AncestralCalm ×0.6, Crosswind ×1.5, AetherStorm ×2.8, VoidSurge ×3.5 (movement cost multipliers).
- **4 sky layers** gated by ship tier: LowSky (tier 1), MidSky (tier 2), HighSky (tier 4), VoidSky (tier 7).
- Islands get deterministic Afrofuturist names (e.g., "Oyasperch", "Kemara's Rest", "The Amaravault").

## Discovery System (three tiers)

Unseen → **Sighted** (enter adjacent) → **Surveyed** (action, reveals danger %) → **Decoded** (action, unlocks a lore fragment + 10 guild reputation). Fog-of-war minimap in the top-right corner: undiscovered = dark, sighted = faint biome hint, surveyed/decoded = full color, ship = white cross.

## Movement & Navigation

- Tap/click an adjacent cell or use WASD/arrows to move; swipe on mobile.
- Movement cost = weather multiplier; ImperialCorridor doubles it.
- Tap any distant discovered cell to auto-navigate: A* pathfinding weighted by weather cost + danger, so routes visibly avoid storms and empire space unless forced through. Auto-nav pauses when an encounter fires.

## Encounters

Space bar or "Scan Sky" button rolls for an event (35% base chance, weighted by layer and biome). One encounter active at a time. **Cooldown rule: the same event cannot re-fire within 3 cells of movement.** Types:

1. **Combat** — turn-based vs. enemy ships (Imperial Interceptor, Sky Pirate Sloop). Six actions: Fire Cannons / Evade / Ascend / Descend / Crew Synergy / Flee. Wind direction rerolls every 2 turns and modifies accuracy. **Crew Synergy chain**: if all three crew perk totals are high, a full chain deals -40% enemy hull in one strike. Enemy AI turns aggressive at low hull.
2. **Discovery** — derelict freighters, ancient ruins: coin loot (20–150), rare artifacts.
3. **Environmental** — Aether Storms and Void Turbulence: hull damage 15–25% unless evaded.
4. **NPC / Faction** — a faction ship hails you; cooperating or refusing shifts standing.
5. **Mythic** (rare, only after 5+ decoded cells, only in CelestialRuin/VoidAnomaly) — vision events that cost 10% hull, unlock gated lore, and permanently alter world danger.

## Factions (5) — standing from -2 Hostile to +2 Allied, shown as icons in the status bar

- **Oya Coalition** (TradeWinds) — founding sky-nation, warm, trade-focused. Neutral greeting: "State your business. We don't stop ships without reason."
- **Kemi Navigators** (AncestorFields, CelestialRuin) — ancestral cartographers. "We trade in knowledge, not gold. What have you found?"
- **Amara Freeholds** (StormRift, Uncharted) — decentralized resistance. "Freeholds don't ask where you're from. Only where you're going."
- **Imperial Syndicate** (ImperialCorridor) — antagonist. "Vessel identified. Present your navigation permit or be boarded."
- **VoidWalkers** (VoidAnomaly) — mythic entities. "You found us. Most don't. The question is what you do with that."

## Quests — branching, morally weighted (Witcher 3 / Vox Machina style)

A "Talk" button appears in the command bar when a quest is available in the current biome. Quests open a dialogue panel: speaker, scene text, 2–3 choice buttons (green = cooperative, red = costly/hostile, slate = neutral). Every choice shifts faction standing, may cost/award coins, may unlock lore, and triggers a crew reaction line in the feed. Build these three:

1. **"The Cartographer's Debt"** (AncestorFields) — Archivist Yemi asks you to smuggle route data the empire wants; if seized it will be used to raze the Amara freeholds. Take the map (then bluff through or dump it at an imperial checkpoint), turn her in (then discover the empire also found an operative list — take the 80-coin reward, or burn it and warn the Amara at your own cost), or walk away. The good choice always has a price.
2. **"What the Corridor Erased"** (ImperialCorridor, tier 2+) — a 40-year-old map shows an island of 2,000 people that newer imperial charts never contained. Investigate: the ruins hold a Kemi cartography station still transmitting a complete pre-imperial atlas to no one. Download it quietly, or broadcast it on all channels and make the empire your enemy.
3. **"The Crew Member's Sky"** (StormRift) — Femi goes quiet: her mother's ship went down in this exact band of sky when she was twelve, and she thinks she's found the wreck. Take her there or tell her it can wait. If you go: board the preserved wreck with her, or hold the ship steady while she goes alone. The stakes are one person. That's why it matters.

## Crew

Three starting crew: **Femi, Amara, Chidi**. Each has a personality (Historian / Gunfighter / Wanderer / Engineer / Mystic / Diplomat / Rebel), an emotional state, and perk bonuses (Accuracy / Damage / CritChance / Cooldown) that strengthen in resonant biomes. Crew react in the feed to combat results, discoveries, hull crises, and quest choices.

## Economy & Progression

- Currency: **Aether Coins** (start 100). Prices ×0.85 in TradeWinds, ×1.4 in ImperialCorridor, no trade in VoidAnomaly.
- Hull repair upgrade: 50 × ship tier. Ship tier advance: 120 × tier (unlocks higher sky layers).
- **Guild**: every decoded cell = +10 reputation to the Kemi Cartographers' Alliance. Tiers: Scout (0) → Pathfinder (150) → Cartographer (500) → SkyMaster (1200). Show tier + rep in the status bar.

## Lore Arc — 6 fragments across 3 eras (the through-line of the whole game)

Era 1 **Age of Unmooring**: "The sky had a floor once. We remember the day it dissolved. Our ancestors did not fall — they rose, and called it liberation." / "Whatever the empire mapped no longer exists. They mapped the wrong things."
Era 2 **Imperial Veil**: "They called it a census. They called it a survey. They called it protection. Each word meant the same thing: your sky is now ours." / "The empire cannot map what does not agree to be seen. We are cartographic refusal." (mythic-gated)
Era 3 **Reconstruction**: "We are not rebuilding what was. We are building what should have been. The difference is everything." / "You found the last piece. The history is complete. What you do with it is the only part we could not predict." (mythic-gated, requires 20 decoded cells)

Completing all fragments in an era triggers a full-screen revelation. Completing all six is the win condition: the sky's erased history is fully reconstructed.

## UI Layout

- **Top status bar**: ◈ Aether Coins (gold) · Guild tier + rep (green) · faction standing icons OYA/KEM/AMR/IMP/VWK with ★▲●▼✕ (Allied/Friendly/Neutral/Wary/Hostile).
- **Top-right**: fog-of-war minimap.
- **Center**: the sky grid, ship rendered as a small glowing vessel with an engine ring, gentle bobbing animation, hull color tinted by current biome.
- **Bottom-left**: scrolling narrative feed (every system writes here — this is the game's voice).
- **Bottom**: context command bar showing only actions valid for the current cell: Survey / Decode / Talk / Barter (TradeWinds) / Attune (AncestorFields) / Ride Storm + Take Cover (StormRift) / Run Dark + Jam Signal (ImperialCorridor) / Salvage (CelestialRuin) / Enter Rift (VoidAnomaly) / Stop Nav.
- **Overlays**: encounter panel (title, intro, Engage button), combat panel (6 action buttons, hull bars, wind indicator), quest dialogue panel, save/load panel (3 slots with timestamp + ship tier, Esc or menu button).
- Hull bar always visible; game over at 0% hull with a "the sky remembers you" epitaph and restart-with-same-seed option.

## Design Rubric (hold every screen to this)

- **Fun**: every biome should *feel* different to be in, not just look different.
- **Replayability**: new seed = new geography, new optimal routes, different quest order.
- **Memorability**: the three quests and six lore fragments are the emotional spine — give them room to breathe (typewriter text, pauses, no rushing).
- **Visual dynamism**: weather animates (drifting particles in storms, shimmer in AncestralCalm); the void pulses.
- **Story cohesion**: everything — pathfinding costs, tariffs, event gating — expresses the same idea: empire suppresses, memory resists, you choose which wins.
