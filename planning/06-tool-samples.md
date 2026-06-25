# Tool Sample Outputs (Phase 3)

Two CLI artifacts shipped to `dayz-stack/tools/dayzstack_tools/cli.py`. Both pull from the local `intel.*` tables (latest available snapshot).

**Install (one-time):**
```bash
cd ~/Dayz/dayz-stack
uv pip install -e ./tools
```

**Entry point:** `dayz-stack <command>` (auto-installed in the workspace venv).

---

## Tool A: `dayz-stack health <server-name-pattern>`

Single-server stack health check. Substring-matches by server name (case-insensitive), picks the most recent snapshot it appears in, and reports:

- **Frameworks** present (CF / Dabs / Expansion-Core)
- **Top deployed mods** on this server, ranked by deployment in the top-200 sample
- **Stale flag** - mods whose Workshop "last updated" is more than 180 days old
- **Rare/bespoke** - mods deployed on fewer than 5 of the top-200
- **Caveats footer** - sample biases, metadata gaps

### Sample run: `dayz-stack health "Bear Mountain"`

```
------------------------------------------------------------------------
  Bear Mountain 1 PVE|MAP WIPE 4 8|BEAR HORDES|UNIQUE|PAPA BEAR
  pop 54/60  rank #122 in top-populated  snapshot 2026-04-25
------------------------------------------------------------------------
  95 mods total  (95 matched to workshop ids)

  Frameworks: Community Framework, Dabs Framework

  Top deployed mods present (rank by deployment in top-200 sample):
    158 servers  CF
    126 servers  Code Lock
    110 servers  Dabs Framework
    100 servers  DeanosBeano
     91 servers  VPPAdminTools
     70 servers  DayZ Editor Loader
     67 servers  BaseBuildingPlus
     61 servers  FlipTransport
    ... and 87 more

  Stale flag (workshop last-updated > 180 days ago):
    1440d stale  on 11 top-200 servers - BBPItemPack
    1148d stale  on  0 top-200 servers - BoomLay's Things
    1140d stale  on 10 top-200 servers - SearchInventory
     921d stale  on 19 top-200 servers - MMG - Mightys Military Gear
     684d stale  on  1 top-200 servers - MMG Civilian Clothing
     549d stale  on 52 top-200 servers - WindstridesClothingPack
    (note: Steam Web API last-updated; sample limited to top-1k pages we pulled)

  Rare/bespoke mods (deployed on <5 of top-200):
    on 1 servers  Animal-Pack
    on 1 servers  CZLRoadConeSnapping
    on 1 servers  FreezesHideout
    on 1 servers  MMG Civilian Clothing
    on 1 servers  Overlay Removal
    on 1 servers  PvZmoD_CustomisableZombies
    on 1 servers  PvZmoD_Spawn_System
    on 1 servers  Tombstone Advanced Groups
    ... and 8 more

  -- caveats --
  - 'top-200' = Battlemetrics top-populated DayZ servers; biased toward heavy-PvE/quest niches
  - workshop metadata limited to mods we've pulled (~30% overlap with deployment-only IDs)
  - one snapshot point - rank/staleness is a single observation, not a trend
```

### What's interesting about this output

- Bear Mountain runs **95 mods** (top-1% mod count) and is **full at 54/60** - heavy stacks work in their niche
- Both **CF and Dabs** present - runs the dual-framework stack (46% of top-200 do this)
- **BBPItemPack on 11 servers, 1440 days stale** - community happily runs ~4-year-stale BBP add-ons
- **Animal-Pack, PvZmoD, Tombstone** are bespoke choices; this admin curates explicit identity

---

## Tool C: `dayz-stack compare <pattern1> <pattern2> [...]`

Cross-server stack comparator. For each pattern, picks the highest-pop matching server. Shows:

- **Mods shared by all servers** - the common foundation, ranked by global deployment
- **Mods unique to each server** - the differentiators, ranked rarest-first
- **BESPOKE flag** on mods deployed on fewer than 5 of top-200

### Sample run: `dayz-stack compare "Bear Mountain" "Noobs Only" "FOG FamilyofGamers"`

```
------------------------------------------------------------------------
  Comparing 3 servers (latest snapshot 2026-04-26)
------------------------------------------------------------------------
  [1] pop  54   95 mods   Bear Mountain 1 PVE|MAP WIPE 4 8|BEAR HORDES|UNIQUE|PAP
  [2] pop  50   95 mods   - Noobs Only - PvE Only - NO PvP -
  [3] pop  67   72 mods   FOG FamilyofGamers | PVE ONLY | FRESH WIPE | HELICOPTER

  Shared by all 3 servers (17 mods):
    158srv  CF
    126srv  Code Lock
    110srv  Dabs Framework
    100srv  DeanosBeano
     70srv  DayZ Editor Loader
     67srv  BaseBuildingPlus
     61srv  FlipTransport
     53srv  RaG_Core
     47srv  CannabisPlus
     46srv  Forward Operator Gear
     45srv  RaG_BaseItems
     44srv  BuilderItems
     41srv  AgricultureCore
     29srv  AmmunitionExpansion
     11srv  BBPItemPack
    ... and 2 more

  Unique to [1] 'Bear Mountain 1 PVE|MAP WIPE 4 8|BEAR HORDES|UNIQU' (54 mods):
    BESPOKE  BearMountain_DonatorGear
    BESPOKE  MuchDecos_Codelock
    BESPOKE  BearMountain_CustomGear
    BESPOKE  BearMountain_Boats
    BESPOKE  Jiggles Signs
    BESPOKE  PG_Retextures
    BESPOKE  zSpawnSelection
    BESPOKE  Pernicek
    BESPOKE  Party On !
    ... and 45 more

  Unique to [2] '- Noobs Only - PvE Only - NO PvP -' (58 mods):
    BESPOKE  Techs 4x4 All Terrain Vehicles
    BESPOKE  Noobs Only Server VP
    BESPOKE  Trader [Inventory Fix]
    BESPOKE  No Shoe Damage
    BESPOKE  Trolley Kart
    BESPOKE  UsefulBatteries
    ... and 52 more

  Unique to [3] 'FOG FamilyofGamers | PVE ONLY | FRESH WIPE | HELIC' (41 mods):
    BESPOKE  FamilyofGamers_Core
    BESPOKE  FamilyofGamers_Helicopters
    BESPOKE  FamilyofGamers_Addons
    BESPOKE  FamilyofGamers_XTS
    BESPOKE  V2 Marquee Letter Signs
    BESPOKE  ParagonClothes
    BESPOKE  StackMoreItems
    ... and 34 more

  -- caveats --
  - workshop_id-based comparison; mods returned without IDs aren't compared
  - 'BESPOKE' flag = on <5 of top-200; not a quality signal, just rarity
  - one snapshot point per server; stacks change between server restarts
```

### What this output reveals

- Three big PvE quest servers share a **17-mod common foundation** (CF, Dabs, CodeLock, BBP, RaG_Core, ...). That's the "cost of entry" stack for the niche.
- Each server has **40-58 mods unique to itself** - the long-tail differentiation is most of the stack
- FamilyofGamers **literally vendor-prefixes their custom mods** (`FamilyofGamers_Core`, `_Helicopters`, etc.) - pro-modder-shop pattern in the wild
- Bear Mountain is the same - `BearMountain_DonatorGear`, `BearMountain_CustomGear`, `BearMountain_Boats`

---

## Why these two specifically

- **Health** is what a server operator would actually run on a fresh build. It says: *here's where you sit relative to the field.* No advice, no judgment - just where the data places you.
- **Compare** validates the differentiation hypothesis: 17 shared, 50+ unique each. Servers that compete in the same niche differentiate hard at the long-tail.

Both have `-- caveats --` blocks. The data is honest about its limits, which is the only way these tools survive an experienced operator's scrutiny.

## Known rough edges (won't fix in v0.6)

- "(unknown)" titles in compare output for mods we don't have workshop metadata for - the 70% gap. Could backfill on demand from Steam Web API.
- Health doesn't show "what % of your stack is mainstream vs bespoke." Would be a useful summary stat. Easy add.
- Server name patterns are case-insensitive substring; no escape for special chars. Fine for ad-hoc use.
- No CSV/JSON output mode. Could pipe markdown to a clipboard tool.
- Stale-flag relies on the partial Workshop snapshot we pulled - a recent update outside our 4 query types won't be reflected. Documented in the caveat block.
