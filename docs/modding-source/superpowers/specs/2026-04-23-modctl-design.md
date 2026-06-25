# modctl - DayZ Mod Dev Workflow & Shop Platform

**Design spec - 2026-04-23 - Author: the developer + Claude (brainstorm transcript in session 2026-04-22)**

> Current implementation note: this document is a design target, not a status report. The repo currently has `doctor`, `build`, `deploy`, `ship`, `serve`, `restart`, `tail`, `watch`, `diagnose`, and `fix` in `tools-extra/modctl`; release/catalog/shop workflows and automated in-game smoke tests are not implemented. Current `ship` is build + deploy, not restart + smoke + tail.

---

## Purpose

Build a command-driven DayZ mod development workflow (`modctl`) that:

1. Replaces the current manual build/deploy/test loop (painful, multi-step, Windows-only scripts) with a single-command pipeline.
2. Is **architecturally ready for a catalog-style mod shop** - catalog metadata, release pipeline, per-mod docs, free "Core" dependency pattern - without prematurely building the shop itself.
3. Is **optimized for Claude Code orchestration**, not just code editing. Structured JSON output mode, categorized error codes, LLM-assisted diagnosis. The part Cursor cannot structurally replicate.
4. Targets the explicit unit economics: ~30 min + ~$15 LLM cost per new mod created through this pipeline.

## Non-goals

- No customer accounts / license keys / payment processing in MVP
- No download portal / shop website in MVP
- No automated DayZ version matrix regression in MVP
- No multi-dev workflow optimizations (no external collaborator in the project yet)
- No DayZ 2 support (build architecture abstracts it; implementation waits until DayZ 2 ships)
- No content-craftsman mods (weapons, clothing, maps) - explicitly not the chosen lane per `research/06`

## Context & references

- Existing repo state at brainstorm time: 9 commits on `bosssignal` branch, 3 mod projects (BossSignal, TrophyHunter on `bosssignal`; HiveAPI on `main`), FastAPI backends, Python test-harness simulator, minimal `.bat` build scripts.
- Strategic frame: `research/06-leverage-points.md`, `research/08-whats-full-and-paid.md`.
- Hive audit: `docs/HIVE-AUDIT.md`.
- Business model reference: established DayZ mod shops in the ecosystem demonstrate that a multi-mod paid catalog with a free "Core" tier is a viable model. Use only neutral, factual prior-art comparison.
- Product framing: telemetry and tooling for DayZ server networks.

---

## 1. Architecture

Three-layer separation:

- **CLI layer** - Typer-based command parser. Thin. Translates user intent to orchestration calls.
- **Orchestration layer** - Domain logic. A "build" is a plan of ordered steps (resolve -> substitute -> compile -> verify -> sign -> copy keys). No shell calls here; uses action-layer primitives.
- **Action layer** - Thin wrappers around external tools: AddonBuilder.exe, DSSignFile.exe, DayZServer_x64.exe, docker, pytest, git.

Benefit: action-layer is boring & swappable (if DayZ Tools changes or DayZ 2 ships, only that layer changes). Orchestration is the load-bearing logic. CLI is the UX.

**Repo location:** `tools/modctl/` - shipped with the repo, extractable to its own project later.

**Stateless between invocations** (except `watch` and `serve --detached`). Minimal state in `.modctl/state.json` (gitignored): last build timestamps, server PIDs, last RPT log path.

**Windows-native, path-abstracted.** Action layer uses `pathlib.Path` throughout; could port to Linux WSL + Bohemia Linux server binaries without touching orchestration.

---

## 2. Command surface

### Lifecycle
- `modctl init` - first-time setup, health check, optional keypair generation
- `modctl new <name>` - scaffold a new mod (future; not MVP)
- `modctl status` - what's installed / built / deployed / running
- `modctl doctor` - deep toolchain verification (DayZ Tools, DayZ Server, CF subscription, keys)

### Per-mod operations
- `modctl build <mod>` - compile + sign
- `modctl deploy <mod>` - copy PBO to local DayZ Server mods dir + keys
- `modctl test <mod>` - backend pytest + simulator scenarios
- `modctl lint <mod>` - static Enforce analysis (missing semicolons, null checks, class refs)

### Aggregate
- `modctl build --all` - `modctl deploy --all` - `modctl test --all`
- Respects `depends_on` topology. Parallel where dependencies allow.

### Runtime / dev loop
- `modctl serve` - boot local DayZ Server with deployed mods
- `modctl restart` - graceful stop + start
- `modctl tail` - colored live RPT log stream
- `modctl watch <mod>` - file watcher -> auto-rebuild + redeploy + restart (flagship dev-loop command)

### Diagnostic
- `modctl diagnose` - parse last RPT errors, produce actionable report
- `modctl fix` - apply proposed fix with diff + approval + verify loop

### Backend
- `modctl backend up` - `modctl backend down` - `modctl backend logs`

### Catalog / release
- `modctl docs <mod>` - generate/update per-mod docs scaffolds
- `modctl changelog <mod>` - draft changelog from git log since last tag
- `modctl release <mod>` - tag + build + test + sign + publish + announce (the shop flagship)
- `modctl catalog` - list catalog state (tier, price, version, last update)
- `modctl announce <mod>` - post release to Discord webhook (plumbing only in MVP)

### Market research (M4+ feature, architecturally supported)
- `modctl scout` - `modctl rank` - catalog planning from public ecosystem signals (e.g. aggregate server mod-usage frequency)

### Production server (M3+ feature)
- `modctl prod deploy/update-mods/backup/players/restart/logs`

### Flagship
- `modctl ship <mod>` - design target is full cycle: build + deploy + restart + smoke test + tail. Current implementation is build + deploy only.

### Global flags
`--mod`, `--all`, `--dry-run`, `--verbose / -v`, `--json`

---

## 3. Configuration - `mods.yaml`

Single source of truth for every mod and backend. Adding a mod = one config edit.

```yaml
version: 1

defaults:
  dayz_tools_path: "C:/Program Files (x86)/Steam/steamapps/common/DayZ Tools"
  dayz_server_path: "C:/Program Files (x86)/Steam/steamapps/common/DayZServer"
  signing_keys_dir: "build-pipeline/keys"
  output_dir: "output"
  pack_only: true
  pbo_prefix_matches_name: true

backends:
  bosssignal:
    kind: fastapi
    dir: "bosssignal-backend"
    tests: "pytest tests/ -q"
    compose_file: null
    health_url: "http://127.0.0.1:6700/health"
  hiveapi:
    kind: fastapi
    dir: "hiveapi"
    tests: "pytest tests/ -q"
    compose_file: "ops/docker-compose.yml"
    health_url: "http://127.0.0.1:8000/health"

mods:
  - name: bosssignal
    source: "../../mods/BossSignal"
    pbo_name: "BossSignal"
    mod_folder: "@BossSignal"
    depends_on: [cf]
    backend: bosssignal
    enforce_config:
      file: "scripts/3_game/BossSignalConfig.c"
      vars:
        SERVER_ID: "server_01"
        BACKEND_URL: "http://127.0.0.1:6700"
        SHARED_SECRET: "${BOSSSIGNAL_SECRET}"
    watch: ["scripts/**/*.c", "config.cpp"]
    catalog:
      tier: free
      price_eur: null
      category: Infrastructure
      description_short: "Server-side boss encounter observability + live dashboard"
      description_long: "docs/bosssignal/README.md"
      changelog: "docs/bosssignal/CHANGELOG.md"
      install_guide: "docs/bosssignal/install.md"
      config_guide: "docs/bosssignal/config.md"
      troubleshooting: "docs/bosssignal/troubleshooting.md"
      core_dependency: true            # the "Core" free-tier dependency (common catalog-shop pattern)

  - name: trophyhunter
    source: "../../mods/TrophyHunter"
    pbo_name: "TrophyHunter"
    mod_folder: "@TrophyHunter"
    depends_on: [cf, bosssignal]
    backend: bosssignal
    enforce_config:
      file: "scripts/3_game/TrophyHunterConfig.c"
      vars:
        SERVER_ID: "server_01"
        BACKEND_URL: "http://127.0.0.1:6700"
        SHARED_SECRET: "${BOSSSIGNAL_SECRET}"
    watch: ["scripts/**/*.c", "config.cpp"]
    catalog:
      tier: paid
      price_eur: 50
      category: Progression
      description_short: "Boss-kill trophies + network-wide leaderboard"
      depends_on_core: bosssignal

  - name: hiveapi
    source: "sdk-enforce/HiveApiMod"
    pbo_name: "HiveApi"
    mod_folder: "@HiveApi"
    depends_on: [cf]
    backend: hiveapi
    branch: main
    enforce_config:
      file: "scripts/4_world/HiveApiConfig.c"
      vars:
        API_URL: "http://127.0.0.1:8000"
        CLUSTER_ID: "cluster_01"
        SERVER_ID: "server_01"
    watch: ["scripts/**/*.c", "config.cpp"]
    catalog:
      tier: paid
      price_eur: 60
      category: Infrastructure
      description_short: "Cross-server character + inventory sync - modern hive"

dependencies:
  cf:
    name: "Community Framework"
    workshop_id: "1559212036"
    mod_folder: "@CommunityFramework"
    required: true

distribution:
  discord_webhook: "${DISCORD_RELEASE_WEBHOOK}"
  download_portal: null
  changelog_style: "keep-a-changelog"
```

**Key design decisions:**
- Flat mod list (not hierarchical) - easy to scan, easy to diff.
- Backends referenced by name - shared backend (bosssignal + trophyhunter) stays DRY.
- Enforce config is declarative - `.c` file is structural source of truth; yaml is value source of truth. Build-time sed substitution.
- Secrets via `${ENV_VAR}` substitution - never in yaml.
- Branch hint (`branch: main` for hiveapi) - modctl warns on wrong-branch builds.
- `core_dependency: true` / `depends_on_core:` - encodes the common free-tier "Core" dependency pattern.

**Loaded + validated on every command start** via Pydantic schema. Fail fast on missing env vars, wrong types, unknown fields.

---

## 4. Execution model

**Every command flow:** PRE-FLIGHT (validate config, check preconditions) -> PLAN (build ordered step list) -> EXECUTE (step-by-step with capture + validate) -> REPORT (human / json output + exit code).

**Subprocess discipline:**
- Timeouts on every `subprocess.run` call
- Never `shell=True`
- Capture stdout+stderr for parsing
- Per-tool parsers (e.g. `parse_enforce_errors()` turns AddonBuilder stderr into structured `{file, line, message, suggested_fix}`)

**Error categories + exit codes:**
```
0   success
10  CONFIG_ERROR       (mods.yaml bad, env var missing)
20  BUILD_ERROR        (AddonBuilder failed, Enforce compile)
21  SIGN_ERROR
30  DEPLOY_ERROR
40  SERVER_ERROR
50  TEST_ERROR
60  IO_ERROR
70  DEPENDENCY_ERROR   (CF missing, wrong branch)
80  CONFLICT_ERROR     (mod-on-mod)
90  UNKNOWN            (escalates to LLM diagnosis)
```

Lets scripts + Claude Code reason about failures without parsing stdout.

**Output modes:**
- Human (default): progress line per step + summary
- JSON (`--json`): structured steps array + result + warnings + errors. This is how Claude Code invokes modctl cleanly in conversations.

**Long-running commands:**
- `modctl watch` - watchdog file observer, 500ms debounce, runs `modctl ship` internally on change. Survives build failures (keeps watching).
- `modctl serve` - spawns DayZ Server, streams server stdout + RPT log with colored tags. Graceful Ctrl+C shutdown.
- `modctl tail` - finds latest RPT, colorizes `[ERROR]/[WARN]/[BossSignal]/...`, hints `modctl diagnose` on error lines.

**State:** `.modctl/state.json` (gitignored). Last build timestamps per mod, server PID (if detached serve), last RPT path.

**Concurrency:** `--all` mode builds in parallel respecting `depends_on` topology, `--jobs N` flag (default CPU count). Deploy/serve/watch are serial - shared resources.

---

## 5. Error diagnosis + `modctl fix`

The structurally-beats-Cursor feature. Two-layer diagnosis:

### Layer 1 - rule-based (fast, free, deterministic)

`tools/modctl/modctl/rules/enforce.yaml`:

```yaml
rules:
  - id: rpt.null_identity_dereference
    match: "NULL pointer to instance.*GetIdentity|killer\\.GetIdentity"
    category: BUILD_ERROR
    severity: critical
    confidence: high
    diagnosis: "Player identity dereferenced without null check"
    fix_template: "wrap in `if (player && player.GetIdentity())` guard"
    can_auto_fix: true     # rule CAN propose a code diff (not just a shell cmd).
                           # All fixes still require user approval by default;
                           # --auto-apply flag (future) bypasses approval for can_auto_fix=true rules.

  - id: rpt.http_connection_refused
    match: "HTTP request failed: Connection refused (127\\.0\\.0\\.1|localhost):(\\d+)"
    category: DEPENDENCY_ERROR
    severity: warning
    confidence: high
    diagnosis: "Backend unreachable at {capture.1}:{capture.2}"
    fix_action: "modctl backend up"       # shell command, not code diff
    can_auto_fix: false                   # still prompts before running the action

  # ... ~20 seed rules; grows organically as LLM-diagnosed fixes are promoted
```

`fix_template` = code diff proposal; `fix_action` = shell command. A rule can have one or the other. **Every fix requires user approval in MVP** - the `can_auto_fix` flag just flags which rules are *candidates* for future `--auto-apply` mode.

Seeds with ~20 rules for the top common Enforce/deploy errors. Every novel LLM-diagnosed fix that works gets promoted to a new rule.

### Layer 2 - LLM-assisted (Claude API) for unmatched errors

- Prompt: error + last 30 RPT lines + 1 referenced source file (~1-3K tokens)
- Response: diagnosis + proposed fix + confidence score (~500-1500 tokens)
- Per-call cost at Claude Opus: ~$0.05-0.15
- Cached in `.modctl/fix_cache.json` keyed by error hash -> zero cost on repeat
- Budget: expect ~10-20 novel diagnoses per new mod; total <$3/mod on diagnosis

### `modctl fix` flow

1. Show proposed diff
2. Prompt `[a]pply, [s]kip, [e]dit, [d]iff context`
3. On apply: `modctl build <mod>` -> verify compile
4. Deploy + restart -> verify server loads
5. `modctl tail --for 10s` -> confirm no new errors
6. Auto-commit: `fix(<mod>): <summary> (modctl rule <rule_id>)`
7. On any verify-step fail: rollback diff, report deeper issue

### The Claude Code orchestration loop (the win vs Cursor)

```
[Save .c .c] -> [watch rebuilds] -> [tail surfaces new error]
  -> [modctl diagnose --json] -> [I read source + propose fix]
  -> [Edit tool applies fix] -> [modctl build + deploy + test]
  -> [verify RPT clean] -> [commit with fix message]
```

Cursor edits files. Claude Code orchestrates the full loop. modctl is what makes the orchestration fast, cheap, reliable.

---

## 6. Catalog + release pipeline (catalog-shop shaped)

### The `modctl release <mod>` flow (9 steps)

```
[1/9] Verifying clean working tree
[2/9] Running full test suite (L1-L5)
[3/9] Building + signing PBO
[4/9] Drafting changelog from git log since vX.Y.Z -> opens editor for polish
[5/9] Bumping version (semver) in mods.yaml + pbo metadata
[6/9] Generating docs (install.md, config.md from source)
[7/9] Git: committing + tagging vX.Y.Z
[8/9] Uploading to download portal (skipped when portal unset - MVP state)
[9/9] Posting to Discord webhook (skipped when webhook unset)
```

Each step skippable (`--no-test`, `--no-announce`) for partial/emergency releases.

### Docs generation

Every mod ships with docs scaffold:
```
docs/<mod>/
|-- README.md
|-- CHANGELOG.md         # auto-appended
|-- install.md
|-- config.md            # auto-generated from enforce_config vars + source
|-- troubleshooting.md
`-- api.md               # infra-tier mods only
```

`config.md` is regenerated every `modctl docs <mod>` - keeps docs in sync with code.

### "Core" pattern enforcement

Paid mods MUST declare `depends_on_core:` pointing to a free mod. BossSignal is the Core. `modctl release` validates the chain before shipping.

---

## 7. Testing strategy (7 layers)

```
L7  Release gate              ← all lower layers must pass
L6  DayZ version regression   ← pre-release only (M4+)
L5  Scripted E2E scenarios    ← test-harness Enforce mod
L4  In-game smoke test        ← on every ship
L3  Enforce static lint       ← no DayZ required
L2  Integration (simulator)   ← FastAPI + simulator round-trip
L1  Unit (backend + modctl)   ← <10s, run on every save
```

### L5 detail - test-harness Enforce mod (MVP feature, clever)

Separate `@TestHarness` mod that only loads with `-testMode=1`:

```c
modded class MissionServer {
    override void OnInit() {
        super.OnInit();
        if (GetGame().ServerConfigGetInt("testMode") == 1) {
            GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY)
                .CallLater(this.RunScenario, 5000, false, "boss_kill_trophy");
        }
    }
    void RunScenario(string name) {
        // Spawn boss -> apply damage -> kill -> assert trophy event
        // Write result to %APPDATA%\DayZ\test_results.json
    }
}
```

Gives programmatic E2E testing *inside* DayZ without client-automation pain. Never distributed to customers.

### L7 release gate checklist

- Working tree clean
- L1 + L2 + L3 pass
- L4 smoke passes on current DayZ
- L5 scenarios pass (if defined for this mod)
- Docs exist + current
- `mods.yaml` version bumped
- Git tag doesn't already exist

`--force` bypasses L3-L7 for emergencies. Flags release as unverified.

### Future (not MVP)

- L6 DayZ version matrix (M4+): switch Steam DayZ Server beta branches, smoke test per version
- CI in GitHub Actions runs L1-L3 on every PR; self-hosted Windows runner for L4-L7 when revenue justifies it

---

## 8. Market research + adjacent stack (M4+ architecturally supported)

Commands supported but not built in MVP:

- `modctl scout --top 100` - pull public server mod lists, frequency-rank mods to understand which categories are in demand
- `modctl rank` - cross-ref public mod-usage frequency × our chosen lanes -> build-next backlog
- `modctl prod deploy/update-mods/backup/players/restart/logs` - the operator's own DayZ prod server mgmt

**Workflow validation:** pick a well-understood mod category (e.g. a leaderboard mod) and build an original implementation through modctl, then measure time + cost + quality. Validates the full pipeline AND seeds the catalog. Use only publicly available, factual prior-art comparison; build original work rather than copying any existing product.

**Scene etiquette:** no code copying, credit inspiration, position as an independent alternative, and compete on architecture + integration + stability. Price fairly.

---

## 9. Extension path / milestones

```
M0  Current            Core local CLI exists. BossSignal/TrophyHunter in-game validation remains a separate milestone.
M1  First release      BossSignal v0.2.0 shipped after validation. `modctl release` is still future work.
M2  HiveAPI revived    main branch mods work through modctl. ~1 month out.
M3  First customer     License mgmt + distribution hooks flip from null to working.
M4  Catalog ≥ 5 mods   TUI, regression matrix, mod scaffolder become worth building.
M5  Extract modctl     Public repo + pip-installable. "The DayZ modder rig."
M6  DayZ 2             Action layer swaps; orchestration + CLI + catalog survive.
```

**Architectural bets that pay off later:**
- 3-layer separation -> DayZ 2 migration = swap action layer only
- `mods.yaml` as truth -> scaffolder, multi-variant, customer configs for free
- `--json` mode -> TUI + web UI + Claude Code all read the same source
- Categorized errors -> public error-KB; crowdsourced rule library
- Release pipeline -> shop publish + Discord announce + email drops plug in cleanly
- Test-harness mod -> automated QA across DayZ version matrix
- Stateless commands -> CI, multi-machine, concurrent dev

**Explicitly deferred (YAGNI):** TUI, multi-variant builds, DayZ version regression, scaffolder, customer-facing shop site, license key validation, Discord webhook payload, download portal, payment processing, auto-update mechanism, multi-dev workflow, DayZ 2 action layer.

---

## 10. Open questions / known unknowns

- **Exact Enforce error patterns to seed L1 rules.** Need first real DayZ Server boots to collect. Will grow organically from first 2-3 mods through the pipeline.
- **Whether `enforce-script-lsp` is mature enough to integrate for L3 lint.** TBD; worth evaluating when L3 is built.
- **Discord webhook payload format + shop metadata.** Design when first customer arrives (M3).
- **DayZ Server path assumptions for Windows.** Default-path assumption in `defaults:`; verify handles Steam's `steamapps` path variations and non-default Steam installs.
- **Concurrent builds from `--all` mode - Addon Builder locking behavior.** Need to test if parallel AddonBuilder invocations contend on shared temp dirs. Fallback: serial for `--all` build, parallel only for test/lint.
- **Claude Opus vs Haiku for diagnosis.** Opus for quality, Haiku for cost. Default TBD after measuring accuracy on seed error corpus.

---

## Acceptance criteria for MVP (M0 -> M1)

1. `modctl build bosssignal` produces a signed PBO in <10s.
2. `modctl deploy bosssignal` copies to local DayZ Server with bikey placed correctly.
3. `modctl ship bosssignal` runs current full implemented cycle (build -> deploy) in <60s; restart + smoke are future validation work.
4. `modctl watch bosssignal` auto-rebuilds on .c save with <20s turnaround.
5. `modctl diagnose` produces structured report on at least 5 seed-rule error patterns.
6. `modctl fix` applies a diff with approval + verify-loop for at least 3 auto-fix rules.
7. `modctl release bosssignal` produces a signed PBO, tagged git release, generated docs, and draft changelog (Discord/portal hooks may be no-op).
8. `modctl --json` output on every command validates against a JSON schema (lets Claude Code parse reliably).
9. All MVP commands have human + json output modes.
10. Documentation exists for every MVP command in `tools/modctl/README.md`.

MVP ships when the implemented local commands pass validation. Release/catalog criteria remain future work until `modctl release` exists.
