# 09 - Market Analysis: Mod Business-Model Patterns

Companion to `08-whats-full-and-paid.md` but narrower and sharper: **for established DayZ mods, document the business-model and engagement patterns that correlate with sustained adoption.** Prior-art analysis only; the goal is to understand the ecosystem, not to displace any specific author.

This doc is a reusable framework. It fills in with publicly available ecosystem data.

---

## Inputs needed before this doc has value

- [ ] **Public Steam/Workshop profile URLs** for relevant mod authors or operators
- [ ] **Established mods** - publicly known, widely adopted DayZ mods worth studying as prior art
- [ ] **Server-count signals** - for each mod, how many servers run it (pull from Battlemetrics mod filter if available)

---

## The 5-lens analysis framework

For each mod or mod-maker, answer these 5 lenses. Skip what's not applicable; don't force a fit.

### 1. Identity
- Mod name + author handle + Workshop URL + mirror elsewhere (DayZSaLauncher, CurseForge, Discord)
- First published date + last updated date
- Dependencies (CF Expansion another mod-maker's framework)
- License / distribution model (Workshop-only, private to paying servers, tiered, open-source)

### 2. Traction
- Steam Workshop subscribers (proxy for server admin adoption)
- Battlemetrics "servers running this mod" (proxy for actual player exposure)
- Growth trajectory: is the subscriber count climbing, flat, or decaying
- Comment velocity on Workshop page - live audience or ghost town
- Discord / external community size if public

### 3. Monetization surface
Four models show up in the scene. Which does this mod use
- **Patreon / donation-driven** - free mod, Patreon for "early access" or "priority support"
- **Private distribution** - mod isn't on Workshop; paying servers get a private PBO. Often tied to the author's hosting service
- **Framework-then-addons** - free core mod, paid extensions or themed packs
- **Indirect leverage** - mod is free but author also sells services: custom mod commissions, server admin work, hosting, Discord bot subscriptions

Estimate revenue magnitude if possible ($0 / hundreds / low-thousands / 5-figure+ per month). Cite evidence.

### 4. Mechanics - what does it actually do
One paragraph describing the gameplay experience. Then break into:
- **Server-side systems** (persistence, RPC, scheduled events)
- **Client-side surface** (new items, new UI, HUD, animations)
- **Admin surface** (config files, commands, GUIs)
- **Integration points** (hooks into Expansion BaseBuilding Trader)

This is a high-level description of publicly observable behaviour, used to understand category conventions.

### 5. Build effort vs moat
The most important lens for the strategy.
- **What's achievable in 1-2 weeks** given our current stack (BossSignal backend, TrophyHunter, AI-coding leverage)
- **What's achievable in 1-2 months** with sustained effort
- **What's moat** - years of asset production (3D models, animations, maps), Bohemia relationships, brand trust, Discord community

Cross-reference against `research/06-leverage-points.md` - does this live in the "content craftsman" lane we shouldn't compete in, or does it have an observability / orchestration / AI angle where a systems-first shape adds value

---

## Output per mod - one section each

Use this template. Keep each under 400 words. Verbose = not useful.

```markdown
## {{Mod name}} - {{Author handle}}

**URL:** https://steamcommunity.com/sharedfiles/filedetails/id=...
**Published:** YYYY-MM-DD - **Last updated:** YYYY-MM-DD
**Subscribers:** NNN,NNN - **Servers running (Battlemetrics):** NNN

### Traction read
{{growth trajectory, comment velocity, evidence of live audience}}

### Monetization
- **Model:** {{patreon / private / framework / indirect}}
- **Estimated monthly:** {{range with evidence}}
- **What players actually pay for:** {{the thing that triggers the wallet}}

### Mechanics
{{one paragraph gameplay description}}

- **Server-side:** {{...}}
- **Client-side:** {{...}}
- **Admin surface:** {{...}}
- **Integrations:** {{CF / Expansion / other}}

### Build effort vs moat
- **1-2 weeks:** {{...}}
- **1-2 months:** {{...}}
- **Moat:** {{...}}

### Strategic relevance
{{does this fit the architect-shaped lane from research/06, or is it content-craftsman territory we should avoid What's the lesson to learn vs. the lane we pass on}}
```

---

## Cross-cutting insights (fill in after 3+ mods analyzed)

Once we've analyzed at least 3 established mods, this section captures the patterns:

### Pricing patterns
Where the money actually comes from across the scene. Price points, what converts free to paid, what doesn't.

### Production quality signals
What "high production value" actually means in DayZ mods in 2026 - is it 3D models, UI polish, config depth, Discord support, update cadence Where's the floor, where's the ceiling

### Distribution strategy
Workshop-first vs Discord-first vs private-server-first. When does each work

### Community-building patterns
How established mod authors recruit playtesters, encourage Workshop reviews, and seed servers. The stuff that isn't in the code.

### Category whitespace
What categories have high demand but few high-quality mods Where's a systems-thinker / AI-tool-user disproportionately advantaged

---

## Operator-integration notes

Fill in once a target server network's public profile and mod list are known:

- [ ] Mod portfolio - list all published Workshop items with attribution
- [ ] Cross-reference external boss classes vs `mods/TrophyHunter/config/bosses.json`
- [ ] Identify which external mods are most adopted by subscriber count
- [ ] Note gaps in the target stack, things not already built that would complement what exists
- [ ] Confirm the stack does not already include a leaderboard before building one

---

## The product shortlist

Seeded from the strategic frame in `research/06-leverage-points.md`. This list updates as we learn the scene. Rank by: (fit to the architect shape) x (scene gap) x (buildable in a realistic timeline).

1. **AI Game Director (mini)** - server-side module reading BossSignal events + player positions, using an LLM to trigger emergent events (heli crashes, zombie hordes, radio broadcasts) based on server tension. Sequel to BossSignal, natural arc.
2. **Weekly Server Chronicle generator** - LLM summary of the week's best encounters as an in-game radio broadcast or Discord post. Low effort, high engagement payoff.
3. **Boss encounter replay / "best-of" board** - tied to TrophyHunter data, shows the most heroic kills with stats. Visual win.
4. **Server-vs-server rivalry tracker** - cross-server leaderboards with weekly resets. Plays into a multi-server network's identity.
5. **AI-assisted bounty generator** - admin types natural language, mod scaffolds a bounty target, spawn location, reward. Native AI-tool leverage.

---

## Status

- **2026-04-22** - scaffold created. No real entries until public profile/mod-author data lands.
