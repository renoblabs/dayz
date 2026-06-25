# 07 - 30/60/90 Plan

Realistic. Rotating 12-hr shifts. Side quest, not pivot. AEA Arena and Echo AI keep priority. First DayZ install + first play happen during Days 1-15. First real mod shipped within 90 days.

The plan is deliberately low-volume: ~4-8 hours/week sustainable, ~15-20 hrs/week on rare "deep dive" days off. If you can hit more, great. The milestones are what matter.

---

## Guiding principles (set once, refer back often)

1. **Don't write Enforce code for the first 30 days.** Read it, play the game, run servers other people built. Playing DayZ _teaches_ the game's rhythm, which is how you know what to build.
2. **Don't touch the `dayzAPI` repo until Day 30+.** Come back to it with informed eyes. Delete 80%. Rebrand. Re-scope to "Signals" (see `06-leverage-points.md`).
3. **Set up a clean project identity by Day 7 and commit.** Use a dedicated GitHub account, Discord account, and email for the project so it stays separate from unrelated work. A separate Steam account is optional (mods can be uploaded from a separate Steam account with DayZ owned).
4. **Lurk before posting.** Do not ask questions in modding Discords for at least 30 days. Read backscroll. By day 60 you've seen the same questions answered 10 times and you can be helpful instead of needy.
5. **No "production-ready" language.** No "HiveAPI 2.0." No badges. Build one small useful thing, let the work speak. Marketing-heavy READMEs are a tell.
6. **Pull any prototype off external/customer servers immediately** if it is still there. `dayzAPI` infinite-retry loop is a plausible suspect for the ticket. Do not be the cause of a second incident.
7. **Every week, one hour of "is this still a side quest" audit.** If you're bleeding time from Arena/Echo, cut scope here. The project is meaningless if your main work suffers.

---

## Project-account setup checklist (do in week 1)

Keep the side project's accounts separate from your main and work identities - standard hygiene for a personal project, nothing more.

- A dedicated project email account.
- A dedicated GitHub account for the project. Set `user.email` and `user.name` per-repo so commits are attributed correctly.
- A dedicated Discord account. Join lurk-only at first.
- A separate Steam account is optional - you can upload Workshop mods from your main account, or use a separate account if you prefer to keep playtime/profile separate.
- Pick a short, memorable project handle. Not too clever. Think `chernoengine` or `blacksignal`.
- Write the handle's one-line bio once: "systems-minded modder focused on observability + tooling." Keep it consistent.
- A separate browser profile for project accounts keeps cookies and sessions tidy.

---

## Day 0 - This weekend (first 2-4 hours)

- **Install DayZ.** Your main Steam account is fine for _playing_.
- **Install DayZ Tools** from Steam (free, separate listing - Bohemia's official modding suite).
- **Run the game once** on a vanilla official server. 30-60 min. Get killed. Get cold. Get hungry. Get dysentery. Feel the rhythm. This is research, not fun (yet).
- **Pull any prototype mod off external/customer servers** if deployed anywhere. Non-negotiable.
- **Create the project-account infrastructure** (above checklist).

---

## Days 1-30 - Recon and Game Fluency

### Goals
1. Play DayZ well enough to have informed opinions.
2. Learn the Bohemia stack from reading, not shipping.
3. Lurk the real Discords.
4. Read the source of 2-3 reference mods.
5. Pick the narrow wedge you'll build.

### What to install (in order)
1. **DayZ** (main account).
2. **DayZ Tools** (for P:\ drive setup, Addon Builder, Workbench).
3. **VS Code** + [vscode-dayz-enforce-script-extension](https://github.com/JeromeK13/vscode-dayz-enforce-script-extension) + [enforce-script-lsp](https://github.com/devz-tools/enforce-script-lsp).
4. **Git** under the project-account config.
5. **SteamCMD** for self-hosting a local test server on Day 20+.
6. Optional: **Docker Desktop** if you want to run your own offline stack.

### What to play (in order)
- **Vanilla official Chernarus** - 3-5 sessions, 2 hrs each. Get to the point of "I died with gear and am mad about it."
- **One modded PvE server** (any CF+Expansion+Trader combo from Battlemetrics top 50). Feel the difference.
- **One hardcore FPP server** - DUG (if they're whitelisting) or similar. Feel the tension vanilla-+ communities chase.
- **Namalsk** at least one session. Feel what Sumrak built. This is the bar.

### What to read (in order)
Priority-ordered reading list:

1. **Bohemia Wiki - DayZ:Modding Basics** -> [Modding Basics](https://community.bistudio.com/wiki/DayZ:Modding_Basics) -> [Enforce Script Syntax](https://community.bistudio.com/wiki/DayZ:Enforce_Script_Syntax) -> [Addon Builder](https://community.bistudio.com/wiki/Addon_Builder) -> [Extensions](https://community.bistudio.com/wiki/Extensions).
2. **DayZ-Expansion EnforceScript Pitfalls wiki** (linked in `04-stack-architecture.md`) - prints out the sharp edges.
3. **DaemonForge UniversalAPI** [source](https://github.com/DaemonForge/DayZ-UniveralApi). Read it. This is your competition in the "external data" space - know it cold before you decide whether to avoid the space (likely) or play in it.
4. **Community Framework** [source](https://github.com/Arkensor/DayZ-CommunityFramework). Especially `docs/RPC/` and `docs/Modules/`. This is the foundation everything else sits on.
5. **MapLink Hive** - read mod description and forum discussion. This is where cross-server persistence lives. Understand why it's hard.
6. **Sumrak's Namalsk-Server repo** on GitHub - cleanly-written DayZ mod author's structure.
7. **DZconfig wiki** (types.xml, events.xml, cfgeconomycore.xml) for Central Economy mental model.
8. **Bohemia Monetization Rules + Game Content Usage Rules** end to end. Know the third rails.
9. **`./research/dayz/04-stack-architecture.md`** (the doc you just got). Re-read twice.

### Discords to lurk (join, never post)
- DayZ Modding Community (D.Z.M.C) - primary.
- Expansion Discord - secondary.
- CFTools / Omega Manager - for ops pulse.
- Bennett's DayZ Modding - console reality check (even if you don't target console).
- Official DayZ Discord - policy and announcement pulse.

Spend 20 min/day scrolling backscroll on D.Z.M.C. Note recurring questions. Note who answers them well (those are the real operators).

### Narrow the wedge (by Day 25)
Re-read `06-leverage-points.md`. Pick **one** project for the first 60 days. Strong recommendation: **DayZ Signals** (option A) - smallest mod footprint, reuses ~70% of `dayzAPI`, maximum systems leverage, zero Bohemia policy exposure.

### Milestone at Day 30
- 10-20 hours of in-game DayZ. Informed opinions.
- Read and can describe: Enforce module system, PBO/signing, CE XML, CF RPCManager, Bohemia monetization rules.
- Lurked D.Z.M.C for 3+ weeks.
- Project accounts set up and clean.
- Old `dayzAPI` decision made: archived (strong recommendation) or re-scoped for Signals.
- One-page design doc in private repo: "What is Signals, what does v0.1 do, what does it NOT do."

---

## Days 31-60 - Build the minimum viable thing

### Goals
1. Ship a working local demo of **DayZ Signals v0.1** end-to-end.
2. Publish nothing yet. Not to GitHub public, not to Workshop, not on Discord. Private.
3. Begin talking in Discord - answer 2-3 beginner questions where you can, using what you learned in Days 1-30. Build the handle's reputation with zero self-promo.

### What v0.1 actually is
- A tiny Enforce mod that uses CF's RPC and hooks a few lifecycle events (player connect, death, kill, damage, logout).
- Each event emits a structured JSON payload to a backend via `CallRestApi()` - real Enforce API, not the one you guessed at.
- Backend is your existing FastAPI (cleaned up: CORS tightened, idempotency preserved, events table kept, everything labeled "Hive" _removed_, admin endpoints kept).
- One simple web dashboard showing live event stream + 1 aggregate (deaths per hour).
- Runs locally against a self-hosted DayZ test server on your machine.

Not v0.1:
- Cross-server state.
- Inventory sync.
- Auth beyond a single shared secret.
- AI director (that's v0.3+).
- Workshop publishing.

### Ordered work (not hours, just sequence)
1. **Stand up a local DayZ test server** via SteamCMD. This is the single most important skill you'll learn - everything else is blocked until you can `start server, watch RPT log, connect with client, see player join event in log`.
2. **Stand up a local backend** from the existing repo, tightened to Signals-shape. Delete `characters/claim`, `inventory/*`, `MoveTicket`, the React UI's `Characters` page. Keep events, SSE, admin overview.
3. **Write the first Enforce event emitter** - target `CF`'s RPC and test against real engine docs this time. Start with one event: `player_connected`. Get that flowing end-to-end.
4. **Expand to 5-6 events.** Kill, death, damage, loot pickup, disconnect. Structured schema.
5. **Tighten the web dashboard** to show just the event stream + one counter.
6. **Test a full loop.** Start backend -> start test server -> connect -> see events stream live in dashboard. This is your "hello world."
7. **Write proper README** under the project handle. Not "production-ready." Something like: "Lightweight server-event telemetry for DayZ. Early alpha. Not ready for production servers yet."

### Discord engagement (low volume)
- Answer 2-3 questions per week where you actually know.
- Do not mention Signals.
- Do not self-promote.
- Ask one question yourself (beginner-honest, not performative) around Day 45, to soften the appearance of "this new handle that only answers."

### Milestone at Day 60
- Local end-to-end demo working.
- Backend rewritten / rescoped.
- Enforce mod compiles, signs, loads, and emits 5+ event types.
- Project handle has ~5 helpful Discord answers logged, zero self-promo.
- Private repo with clean commit history under the project account.
- One-page "v0.1 release plan" written.

---

## Days 61-90 - Ship it

### Goals
1. Publish Signals v0.1 publicly under the project handle.
2. Collect first 10 users (server admins who install it locally).
3. Decide whether to push to v0.2 (more events + richer dashboard) or v0.3 (AI Director layer).

### Publishing checklist
- Finalize LICENSE (MIT or Apache-2.0 is fine for this).
- Write clean `README.md`: what it is, what it is not, how to install, screenshots, disclaimer.
- Generate signing keys (`.biprivatekey`, `.bikey`, `.bisign`). Protect the `.biprivatekey`.
- Build PBO with Addon Builder or pboProject, signed.
- Publish to **GitHub first** (code + signed PBO release). Not Workshop yet.
- Post **once** to D.Z.M.C Discord in the appropriate #releases channel. One sentence. Link to repo. No hype.
- Post **once** to r/dayzmod or similar, same message, same restraint.
- Do not post to the Expansion Discord (wrong audience, they're busy, looks like spam). Let it reach them via secondary ripples.

### What will probably happen
- 3-5 people try it. Most won't report back.
- 1-2 people find bugs / incompatibilities. Respond politely, fix, ship 0.1.1.
- Someone asks "is this like UniversalAPI" - answer honestly: "No, it observes events; UAPI stores state. They pair well."
- Someone asks about monetization. Answer: "Free, MIT, self-host."
- Someone accuses you of being a data-collection scheme. Explain clearly in the README that data stays on the server admin's own backend.
- If the mod catches on, someone may reupload it. Decide your reuploading policy in advance and state the license clearly.

### Deciding v0.2 vs v0.3
- If v0.1 has 5+ active users by Day 90 -> push to v0.2 (more event types + starter dashboard for common queries). You have product-market traction; make the product better.
- If v0.1 has 1-2 users -> don't add scope. Instead, write one blog post under the handle that explains _what you learned_ about server-event telemetry in DayZ. Build reputation, plan v0.2 for months 4-6.
- Either way, **do not start the AI Director until v0.1 has real users**. The director is the moat, but moats are meaningless without a castle.

### Milestone at Day 90
- Signals v0.1 published under the project handle.
- GitHub + signed PBO release.
- 1-2 Discord posts, 1 Reddit post, zero hype.
- First real users (or clean data that says "no one cares, pivot").
- Project handle has ~15 helpful Discord answers, 1-2 blog posts or gists explaining something useful.
- Decision made about v0.2 direction.

---

## What happens at 90+ days (preview, not commitment)

If Signals takes: Director (AI game director) becomes v0.3. This is the differentiator and the flagship candidate.

If Signals doesn't take: Pivot to **DayZ Atlas** (Workshop discovery engine) - pure web product, no in-game component, zero Bohemia exposure, much lower-risk. Use the mod knowledge you built as the data pipeline.

Let the work speak for itself. Don't push for attention at v0.1 or at 10 users. The strongest position is when the community is saying "this thing is actually useful" on its own. Could be month 6, could be month 18.

---

## Time-budget sanity

12-hr rotating shifts means some weeks you'll get 15 hours and some you'll get 2. The plan above assumes **average 6 hrs/week** over 90 days = ~78 hours. That's enough for all of the above if you're ruthless about scope. It's not enough if you try to be a real Enforce modder. Don't try to be. Be an architect with a mod attached.

Arena and Echo come first. Every week. If a milestone slides 2 weeks, that's fine. If it slides 8 weeks, re-check whether you still want to do this. Honest check-ins beat sunk-cost momentum.

---

## Anti-goals (things to explicitly not do)

- **Don't rename the repo "Signals" while leaving `HiveAPI` branding internally.** Do the rebrand cleanly or archive and restart.
- **Don't publish Signals to Steam Workshop in the first 90 days.** GitHub only. Workshop invites DMCA abuse.
- **Don't take donations, Patreon, or any form of payment in the first 90 days.** Not because it's banned (it's mostly not) but because money + an unproven early-alpha mod invites the worst kinds of attention.
- **Keep the side project and your main/work presence separate.** Don't cross-promote a v0.1 alpha into unrelated channels; let it stand on its own.
- **Don't try to do all of this on shift.** You'll miss things in-game and in-ticket that you'd have caught rested.

---

## Reference: all seven deliverables

| File | Purpose |
|---|---|
| `01-repo-inventory.md` | Every file, purposes, stack signals from your old repo |
| `02-original-intent.md` | What you were actually trying to build |
| `03-what-was-broken.md` | Diagnosis, bluntly |
| `04-stack-architecture.md` | Deep read of the Bohemia/DayZ modding stack |
| `05-scene-map.md` | Who matters, where they hang out, current drama |
| `06-leverage-points.md` | Where your specific shape wins |
| `07-plan.md` | This doc |

Read 03 and 06 together. That pair is the strategic pivot from "blind prototype" to "aimed shot."
