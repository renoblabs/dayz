# Corpus Quality Check & Server Intel Ground-Truth (Session 5)

**Run:** 2026-04-26 ~21:00 EDT
**Corpus state:** 3,396 sources / 8,201 chunks. **7,322 of 8,201 chunks still unembedded** (Ollama background fill restarted this session; was dead between sessions 4 and 5). Hybrid retrieval is currently BM25-dominant.

---

## KB retrieval quality - verdict

### In-domain Enforce queries -> strong

| query | top hit | score | retrievers |
|---|---|---|---|
| `modded class MissionGameplay` | CommunityFramework `missionserver/communityframework/mission/missiongameplay.c` (the literal source) | 0.0282 | bm25=9 + vec=13 |
| `OnEntityKilled` | salutesh Expansion Quests `ExpansionQuestObjectiveAICampEvent.c` | 0.0164 | bm25 only |
| `RPC server client` | the  `research/04-stack-architecture.md` RPC section | 0.0318 | bm25=5 + vec=1 |
| `cfgspawnabletypes loot` | the  `research/04-stack-architecture.md` Central Economy section | 0.0164 | vec only |

Top hits are useful and citation-grade. BM25 dominates as expected before vector embeddings catch up.

### Server-intel queries -> also strong

| query | top hit | score |
|---|---|---|
| `types.xml lifetime` | the  `research/05-scene-map.md` - vehicle persistence + lifetime tweaks | 0.0328 (both retrievers) |
| `cfgspawnabletypes attachments` | CE architecture doc | 0.0164 (vec only) |
| `economy nominal min restock` | CE architecture doc | 0.0325 (both retrievers) |
| `mission init.c spawn point` | DayZ modding patterns gotcha (timing) | 0.0164 (vec only) |

Server-pivot queries hit the right corners of the corpus. Once embeddings finish, hybrid quality goes up further.

### Out-of-domain queries -> ⚠ technically returns hits but at noise floor

| query | top hit | score |
|---|---|---|
| `Kubernetes deployment` | TrophyHunter Pre-Deployment Checklist (matched "deployment") | **0.0164** |
| `React state management` | CF `weapon_base.c` `CF_SyncSelectionState` (matched "state") | **0.0164** |
| `Postgres replication` | the  `03-what-was-broken.md` (matched "broken") | **0.0164** |

**Score discriminates correctly: in-domain hits are 0.025-0.033, out-of-domain hits are exactly 0.0164** = `1/(60+1)` = the RRF floor for one retriever returning ONE result. The score IS the signal - but the CLI prints results without a confidence indicator, which could mislead a casual user into trusting noise.

### Recommended adjustments

- **Add `--min-score` CLI option** (default ~0.020) so out-of-domain queries return "(no confident hits)" instead of garbage at the floor.
- **Add a confidence band to MCP tool output** - `"confidence": "high" | "medium" | "low"` derived from RRF score relative to noise floor. Agents should be able to ignore low-confidence results without parsing scores.
- **Vector embeddings catching up will tighten the floor** - expect quality to improve as 7322 unembedded chunks get filled.

Both are session-5 hygiene items, not blockers.

---

## Server intel ground-truth - top 30 most-deployed mods (2026-04-25 snapshot, top 200 servers)

```
workshop_id |           mod_name            | servers_running | pct_of_top_200 
-------------+-------------------------------+-----------------+----------------
 1559212036  | Community Framework           |             154 |           77.0
 1646187754  | CodeLock                      |             120 |           60.0
 2545327648  | Dabs Framework                |             112 |           56.0
 2054775140  | Inkota                        |              89 |           44.5
 1828439124  | VPPAdminTools                 |              84 |           42.0
 1797720064  | WindstrideClothing            |              73 |           36.5
 2276010135  | DEL                           |              67 |           33.5
 2116157322  | DayZ-Expansion-Licensed       |              58 |           29.0
 1832448183  | FlipTransport                 |              57 |           28.5
 1710977250  | BaseBuildingPlus              |              55 |           27.5
 2291785308  | DayZ-Expansion-Core           |              52 |           26.0
 2143128974  | Advanced Weapon Scopes        |              46 |           23.0
 2931560672  | Forward Operator Gear         |              46 |           23.0
 3556131153  | RaG_Core                      |              44 |           22.0
 1827241477  | Breachingcharge               |              44 |           22.0
 2291785437  | DayZ-Expansion-Vehicles       |              43 |           21.5
 2572328470  | DayZ-Expansion-Market         |              41 |           20.5
 2918418331  | Survivor Animations           |              40 |           20.0
 2828486817  | DayZ-Expansion-Quests         |              40 |           20.0
 1565871491  | BuilderItems                  |              39 |           19.5
 2878980498  | RaG_BaseItems                 |              38 |           19.0
 1314079816  | Inkota                        |              35 |           17.5
 2819373632  | BodyBags                      |              35 |           17.5
 2793893086  | DayZ-Expansion-Animations     |              34 |           17.0
 1564026768  | Community Online Tools        |              33 |           16.5
 2303554682  | Dogtags                       |              32 |           16.0
 1932611410  | CannabisPlus                  |              32 |           16.0
 892619329   | BBP                           |              31 |           15.5
 2651195301  | Arma 2 Helicopters Remastered |              29 |           14.5
 2792984177  | DayZ-Expansion-Missions       |              29 |           14.5
```

### Sanity checks against external claims

[done] **CF dominates as expected** - 77% of top-200 servers run it. This is *exactly* the "foundational dependency, never compete" signal from the master plan's research artifacts.
[done] **Dabs Framework + VPP + CodeLock** = the operational/admin baseline. 56-60% of top servers all run them.
[done] **Expansion is split into 7 packages** in the top 30 (Licensed, Core, Vehicles, Market, Animations, Quests, Missions) - confirms the modular `0_*_Preload` pattern + that operators cherry-pick which Expansion modules they want.

### Strategic reads from this single snapshot

**Operational layer (CF + Dabs + VPP + CodeLock)** is fully solved by existing players. Don't compete.

**Content layer is fragmented** - WindstrideClothing (37%), Forward Operator Gear (23%), Survivor Animations (20%), BuilderItems (20%), RaG_BaseItems (19%), CannabisPlus (16%), Dogtags (16%). Long tail of niche content packs. **A bundled or curated content stack is a genuine market opportunity** - operators have to evaluate dozens individually.

**`Inkota` appears TWICE** as different workshop_ids (2054775140 and 1314079816) but same name. Two community forks of the same mod, both running on populated servers. Suggests a maintenance fork situation worth investigating.

**Helicopters etc.** show up at 14.5% - niche but persistent demand.

**What's NOT here that should be** - TraderPlus / Trader appears in the corpus references but didn't make top 30 by `workshop_id`. Possible explanation: TraderPlus is the dominant trader mod but most servers run it as a *local mod*, not a Workshop subscription. (Battlemetrics only sees Workshop IDs.) **Worth checking with another snapshot or by `mod_name LIKE '%trader%'` query.**

### Forward signals (watch these over the next 2 weeks of snapshots)

- Which mods gain server-share fastest (= rising velocity in `server_mods` count)
- Which mods are losing share (a signal of shifting operator preferences)
- Whether new Expansion packages (1.30 Badlands due late 2026) shift the Expansion split
- Whether RaG_Core's adoption (22%) keeps growing - it's a newer framework
