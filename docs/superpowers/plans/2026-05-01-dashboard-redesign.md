# Plan: DayZ Ops Dashboard - Full Redesign Implementation

Recreate the DayZ Ops Dashboard inside `frontends/web-ui/` per the high-fidelity design reference handed off by the parallel design session. Industrial / military / amber-on-gunmetal operator panel aesthetic - the user has explicitly rejected "clean modern SaaS" and "cyberpunk neon." Pixel-faithful recreation is the bar.

## Project Context

- **Repo:** `~/Dayz/dayz/` (Windows, bash on win32)
- **Working dir for this plan:** `~/Dayz/dayz/frontends/web-ui/`
- **Branch:** `main`
- **Stack:** React 18 + Vite 5 + TypeScript 5 + React Router 6 + axios + lucide-react + recharts + date-fns + Tailwind 3 (all already in `package.json`). React Query (`@tanstack/react-query`) is REQUIRED by the design but NOT yet installed - Task 1 adds it.
- **Backend (already running, do not modify):** `http://127.0.0.1:6700` - BossSignal FastAPI with all 9 routes the design contract needs (server status, events, events SSE stream, leaderboard, encounters, system health, kb sources/search/source-by-id).
- **Tunnel (already running):** `https://your-tunnel.ngrok-free.app` - same backend, public.

## Where to look - design reference materials (DO NOT EDIT THESE FILES)

All design reference files are STAGED at:
```
~/Dayz/dayz/_design-handoff-staging/design_handoff_dayz_ops_dashboard/
```

Contents:
```
README.md               - 19KB build spec; this plan supersedes its DoD
DayZ Ops Dashboard.html - Babel-standalone prototype; mounts <App>
styles.css              - 17KB design tokens + chrome utilities (SOURCE OF TRUTH for color palette)
data.jsx                - mock arrays + ACCENT_HUES + useFakeEventStream
icons.jsx               - Sigil, PlayerAvatar, MapSilhouette, source-type icons (SVG-as-JSX)
panel-server.jsx        - Server Status panel ("fully realized" reference; copy patterns from here)
panels.jsx              - Hero, OPS layout, Event Feed, Leaderboard, Encounters timeline, Health Strip
panel-kb.jsx            - KB browser (Browse / Search / Read modes)
pages-extra.jsx         - Players, Servers, Encounters (full), Trophies, Alerts, Settings
tweaks-panel.jsx        - runtime tweaker (hue / density / grain / scanlines)
```

The design's README is comprehensive - read it once before starting any task. The README's hex-code color block IS STALE. Use `styles.css` as the source of truth: it ships `oklch()` values (e.g. `--amber: oklch(0.62 0.19 28)` - rust red, called "blood rust" in body copy, NOT the warm `#d97e2b` orange the README's tokens block says). When the README and styles.css disagree, **styles.css wins.**

## Backend Contract - already live

Each design panel maps to a real route. All return JSON. All include an `is_mock: true|false` flag (or `kb_available: true|false` for KB) - the UI should show a small "demo data" badge when `is_mock` is true.

| Route | Status | Shape |
|---|---|---|
| `GET /api/v1/server/statusserver_id=` | live, real for server_01 | see `app/routers/dashboard.py` |
| `GET /api/v1/events...` | live | already existed |
| `GET /api/v1/events/stream` | live SSE | already existed |
| `GET /api/v1/leaderboard/boss-killsdays=7&limit=10` | live, mock | rows[] with rank/player_id/player_name/boss_kills/fastest_kill_sec |
| `GET /api/v1/encounters/recentlimit=20` | live, mock | items[] with full encounter fields |
| `GET /api/v1/system/health` | live, real | bosssignal_db / kb_db / kb_corpus / snapshotter rollup |
| `GET /api/v1/kb/sourcestype=&page=&page_size=` | live, real | 3,396 sources |
| `GET /api/v1/kb/searchq=&limit=` | live, real | BM25 over chunks.text_tsv |
| `GET /api/v1/kb/source/{id}` | live, real | source + all chunks |

Field-name mismatches between design's expected shape and actual API exist (e.g. design wants `ServerStatus.name`, API returns `server_id`). Task 5 builds the adapter layer. **Do not modify the backend in this plan** - adapt at the frontend boundary.

## Existing frontends/web-ui state (will be replaced)

The current scaffold is the old HiveAPI dashboard:

```
frontends/web-ui/src/
|-- App.tsx                   # routes: /dashboard /events /hive  (will be replaced)
|-- App.css
|-- index.css                 # minimal Tailwind base (will be expanded)
|-- main.tsx
|-- api/client.ts             # axios client (keep, extend)
|-- components/{Layout,LoadingSpinner,StatCard}.tsx  (legacy, archive)
|-- hooks/useApi.ts           # polling-based hooks (keep useServers/useEvents, ADD useEventStream)
|-- lib/time.ts
|-- pages/{Dashboard,Events,Hive}.tsx  (legacy, archive)
`-- types/index.ts            # ServerStatus / Event / etc. - extend, do not delete
```

Old pages stay in place until **Task 10** archives them. New work happens in NEW files / directories alongside.

## Critical Guard Rails (apply to EVERY task)

1. **DO NOT push to remote.** A repo hook blocks pushes to `main` regardless. Just commit; the user pushes manually after review.
2. **DO NOT touch `dayz-memory/hooks/auto_capture.ps1`.** Parked, off-limits this run.
3. **DO NOT modify the backend.** All required routes already live at `:6700`. Adapt at the frontend boundary in Task 5.
4. **DO NOT skip the tweaks panel** (Task 9). Hue palette + density + CRT/grain are core delight features, not deferrable polish.
5. **DO NOT change realistic mock-data names.** The design's `data.jsx` uses intentional flavor names (e.g. `tisy_hermit`, `Coast_Bambi`, `BossZombie_Tank`). Preserve verbatim - do not regenerate, simplify, or replace with `Player1`/`Zombie1`.
6. **DO NOT strip image assets.** Boss icons, map silhouettes, avatar shapes - copy SVG markup from `icons.jsx` to the new TS components verbatim.
7. **USE `styles.css` as the source of truth for color tokens**, NOT the README's hex block (which is stale per a prior session's audit).
8. **FOLLOW the README's "high-fidelity, pixel-faithful, recreate exactly" mandate.** No simplifications. The corner ticks, stencil headers, scanline overlays, sharp 0px radii - all intentional.
9. **COMMIT PER TASK** with a clear conventional-commit message. The user wants to read the log tomorrow and understand exactly what shipped per chunk.
10. **DO NOT skip task validation.** The validation commands run after each task. If they fail, fix the regression in the same task before committing.
11. **Hard blocker policy:** if a task hits a genuine "I don't know how to proceed" moment (NOT a debug speedbump - a real conceptual ambiguity), STOP. Document at `planning/dashboard-build-blocker-2026-05-01.md` with: which task, what's ambiguous, what you tried, what input is needed. End the run cleanly. Don't iterate in the dark for 2 hours on a question that should bounce to the human.

## Validation Commands

These run after every task. Frontend-only validation; backend is not being changed.

- `cd frontends/web-ui && npm install` (idempotent - only does work after Task 1; otherwise no-op)
- `cd frontends/web-ui && npx tsc --noEmit`
- `cd frontends/web-ui && npm run lint -- --max-warnings 50`

Note on lint: package.json sets `--max-warnings 0`. Override to 50 during the build to allow temporary unused-import warnings between tasks. Final task tightens this back to 0.

---

### Task 1: Foundation - deps, design tokens, Tailwind config, base CSS

Install `@tanstack/react-query` and port the design's color/typography/spacing tokens into the Tailwind config so subsequent tasks can use utility classes that match the design system exactly.

- [ ] `cd frontends/web-ui && npm install @tanstack/react-query@^5`
- [ ] Read `_design-handoff-staging/design_handoff_dayz_ops_dashboard/styles.css` end-to-end. Note every CSS custom property in `:root` - colors (oklch), fonts, geometry, --grain-opacity, --glow-strength.
- [ ] Update `frontends/web-ui/tailwind.config.js`:
  - Replace the `primary.*` color scale with the full design palette under `theme.extend.colors`: `bg.{0,1,2,3,inset}`, `line.{DEFAULT,soft,hard}`, `fg.{DEFAULT,2,3,4}`, `amber.{DEFAULT,soft,line}`, `ok`, `warn`, `bad`, `idle`, `info` - mapped to the oklch() values from styles.css (Tailwind 3 accepts oklch as arbitrary values; use template literals if needed, or via CSS custom property references).
  - Add `theme.extend.fontFamily`: `display: ['Oswald', 'Bebas Neue', 'sans-serif']`, `body: ['Inter', 'system-ui', 'sans-serif']`, `mono: ['JetBrains Mono', 'IBM Plex Mono', 'ui-monospace', 'monospace']`.
  - Add `theme.extend.borderRadius`: `sm: '2px'`, `md: '3px'`, `lg: '4px'`. (Sharp; the design uses 0px in many places - utility class `rounded-none` covers that.)
  - Spacing scale: extend with custom values matching the design's 4 / 6 / 10 / 14 / 18 scale where Tailwind doesn't already cover them.
- [ ] Replace `frontends/web-ui/src/index.css` body so the page sets `--bg-0` background, `--fg` text, mono/body/display CSS variables, and includes the film-grain SVG `body::before` and vignette `body::after` from styles.css. Keep `@tailwind base/components/utilities` directives.
- [ ] Add a Google Fonts `<link>` for Oswald + Inter + JetBrains Mono in `frontends/web-ui/index.html` `<head>`.
- [ ] **DoD:** `npx tsc --noEmit` passes, `npm run dev` starts without errors, the `<body>` background is dark gunmetal-green (oklch 0.14), the page has visible film grain, custom fonts load.
- [ ] Commit: `feat(web-ui): foundation - react-query, design tokens, tailwind config, font/grain base`

### Task 2: Custom chrome utilities - corner ticks, panel frames, dot.live, CRT scanlines

The design uses heavily custom chrome that doesn't map to standard Tailwind: panels with corner-tick L-brackets, stencil headers with leading amber pip, pulsing dot.live halos, CRT scanline overlay. Port these as `@layer components` utilities so panel JSX can use them as classes.

- [ ] Create `frontends/web-ui/src/styles/chrome.css` (imported by `index.css`) and port from `_design-handoff-staging/.../styles.css`:
  - `.panel` - `1px solid var(--line)` on `var(--bg-1)`, no radius, position: relative.
  - `.panel-header` - 36px tall, `var(--bg-2)` bg, leading `.corner` pip (small amber square), uppercase Oswald 11-13px / 0.14em tracking.
  - `.tick-corners` - `::before/::after` L-brackets (8-10px) in each corner, `var(--line-hard)`.
  - `.dot` (base) and modifiers `.dot-live`, `.dot-ok`, `.dot-warn`, `.dot-bad`, `.dot-idle`. The `.dot-live` variant has 1.6s ease-in-out pulsing `box-shadow` halo.
  - `.crt-overlay` - `position: fixed; inset: 0; pointer-events: none;` repeating-gradient horizontal scanlines, opacity controlled by `--glow-strength`.
  - `.grain-overlay` - already in `index.css` body::before from Task 1; expose as a class too.
  - `.event-row.is-new` - slide-in keyframe (`translateY(-8px)` -> 0 + amber `box-shadow` flash, 600ms ease-out).
  - `.btn-ghost`, `.chip`, `.bar` (population/proportion bars), `.stat-cell` - minimum set seen across panels.
- [ ] Wire `chrome.css` into `index.css` via `@import "./styles/chrome.css";` ABOVE the Tailwind directives.
- [ ] Add a quick visual smoke route: a stub component at `src/components/_chrome-test.tsx` that renders one of each utility in a panel, briefly visible at route `/__chrome-test` (TEMPORARY - this route is removed in Task 4 once App.tsx is rewritten).
- [ ] **DoD:** `npx tsc --noEmit` passes; `npm run dev` shows the test route with all chrome utilities rendering correctly. Corner ticks visible. `.dot-live` pulses. Scanline overlay toggles via `--glow-strength` CSS var.
- [ ] Commit: `feat(web-ui): custom chrome utilities (panel, tick-corners, dot-live, crt-overlay, event-row)`

### Task 3: Real SSE hook - useEventStream against /api/v1/events/stream

Replace the design prototype's `useFakeEventStream` with a real `EventSource` subscription that integrates into a React Query cache. New events prepend; stream auto-reconnects on disconnect.

- [ ] Set up the React Query provider in `src/main.tsx`: import `QueryClient`, `QueryClientProvider` from `@tanstack/react-query`, instantiate a single client with `defaultOptions: { queries: { staleTime: 10_000, refetchOnWindowFocus: false } }`, wrap `<App />` in the provider.
- [ ] Create `src/hooks/useEventStream.ts`:
  - Exports `useEventStream(opts: { paused: boolean })` returning `{ events, isConnected, reconnect, pause, resume }`.
  - Uses `EventSource('/api/v1/events/stream')` if same-origin, else `${VITE_API_BASE}/api/v1/events/stream`.
  - On message: parse JSON, prepend to `events` array (capped at 500 to bound memory), update React Query cache key `['events','stream']` so any consumer auto-rerenders.
  - On error: set `isConnected=false`, attempt reconnect after 2s linear backoff (cap 10s).
  - On `paused: true`: close the EventSource; new events buffer locally, drained when un-paused.
  - Cleanup on unmount: close EventSource, clear timeouts.
- [ ] Add `VITE_API_BASE` to `frontends/web-ui/.env.example` (commit), defaulting to `http://127.0.0.1:6700`. Real `.env` is gitignored.
- [ ] Update `src/api/client.ts` to use `import.meta.env.VITE_API_BASE` for the axios base URL (fall back to relative paths for same-origin in production).
- [ ] **DoD:** `npx tsc --noEmit` passes. With backend running at `:6700` and dev server up, the hook successfully connects (EventSource readyState === 1). Logs show heartbeat events arriving every ~30-100s. Pause/resume toggles work.
- [ ] Commit: `feat(web-ui): real SSE useEventStream hook + react-query provider`

### Task 4: App router rewrite - 8 tabs replacing /dashboard /events /hive

Replace the existing 3-route App.tsx with the design's 8-tab structure. Each tab is a route. Build STUB page components for tabs 5-8 (TROPHIES / ALERTS / KNOWLEDGE / SETTINGS) plus 1-4 (OPS / SERVERS / PLAYERS / ENCOUNTERS) that render a placeholder panel - they'll be filled in by Tasks 6-9. This task ensures the app COMPILES and ROUTES at every intermediate state.

- [ ] Create stub files in `src/pages-v2/` (NEW directory - old `src/pages/` archived in Task 10):
  - `OpsPage.tsx`, `ServersPage.tsx`, `PlayersPage.tsx`, `EncountersPage.tsx`, `TrophiesPage.tsx`, `AlertsPage.tsx`, `KnowledgePage.tsx`, `SettingsPage.tsx`.
  - Each stub returns a single `.panel` div with header `<TabName>` and body `"// stub - wired in Task N"`.
- [ ] Create `src/components/TopRail.tsx` with the 48px top-rail per the design (see `panels.jsx` `<TopRail>` and `DayZ Ops Dashboard.html`):
  - Sigil mark (left) - copy the SVG markup verbatim from `icons.jsx` `Sigil`.
  - 8 nav tabs (`OPS / SERVERS / PLAYERS / ENCOUNTERS / TROPHIES / ALERTS / KNOWLEDGE / SETTINGS`), each `<NavLink>` from React Router so active state styles correctly. Active = amber text + amber 2px underline + amber `box-shadow` glow. Inactive = `var(--fg-3)`.
  - Right cluster: SSE connection dot (driven by `useEventStream().isConnected`), search hint `(/)`, Connect/Pause toggle button (toggles the SSE pause state), live UTC clock in mono (re-renders every second).
- [ ] Register global keyboard shortcuts for tab navigation in `src/hooks/useGlobalShortcuts.ts`: `g e` -> ops, `g s` -> servers, `g p` -> players, `g n` -> encounters, `g t` -> trophies, `g a` -> alerts, `g k` -> knowledge, `g ,` -> settings, `/` -> focus search. Use `useEffect` with `keydown` listener and a small "first key seen" buffer that times out after 1s. Help overlay `` -> flagged TODO, do not implement.
- [ ] Replace `src/App.tsx`:
  - Import `BrowserRouter`, `Routes`, `Route`.
  - Render `<TopRail />` (always visible) + `<Routes>` with 8 routes mapping to the 8 stub pages above. Default `/` redirects to `/ops`.
  - Wrap in QueryClientProvider (already added in Task 3 main.tsx - verify and don't double-wrap).
- [ ] Remove the temporary `/__chrome-test` route from Task 2 (the chrome utilities are visible in real panels now).
- [ ] **DoD:** `npx tsc --noEmit` passes. `npm run dev` starts. All 8 routes are reachable via top-rail clicks AND keyboard shortcuts. Active-tab style is amber + underline. SSE dot lights up green when connected. UTC clock ticks. Stub pages render `// stub` placeholder panels.
- [ ] Commit: `feat(web-ui): 8-tab App router + TopRail + global keyboard shortcuts`

### Task 5: Adapter layer - bridge design shapes to real API responses

The design's expected mock-data shapes diverge from what the BossSignal backend actually returns. This task creates a thin adapter layer in `src/api/` that maps API responses to the shapes panels consume, plus a typed React Query hook per route.

- [ ] Read `_design-handoff-staging/design_handoff_dayz_ops_dashboard/data.jsx` end-to-end. Note every mock data shape used by panels.
- [ ] Read the `// Mock Data Shapes (= Backend Contract)` block in the design README.
- [ ] Read each backend route's actual response shape - either from `backends/bosssignal-backend/app/routers/dashboard.py` and `kb.py` source, or by curl-ing each route at `http://127.0.0.1:6700/...`.
- [ ] Extend `src/types/index.ts` with the design-shape interfaces: `ServerStatusUI`, `EventUI`, `LeaderboardEntryUI`, `EncounterUI`, `KbSourceUI`, `KbSearchResultUI`, `KbSourceDetailUI`, `HealthCheckUI` - all suffixed `UI` to distinguish from raw API types if needed.
- [ ] Create `src/api/adapters.ts` with named exporters mapping API -> UI:
  - `adaptServerStatus(api): ServerStatusUI` - maps `server_id` -> `name` (use server_id as name fallback), `last_seen` -> `last_heartbeat`, fills missing `loaded_mods: null`, `perf: null`, `map: null` (UI shows empty state for nulls).
  - `adaptEvent`, `adaptLeaderboard`, `adaptEncounter`, `adaptKbSource`, `adaptKbSearchResult`, `adaptKbSourceDetail`, `adaptHealth`.
  - Each adapter is pure, type-safe, and handles `null`/`undefined` gracefully.
- [ ] Create `src/hooks/useDashboardData.ts` exporting React Query hooks per panel: `useServerStatus(serverId)`, `useLeaderboard(days)`, `useRecentEncounters(limit)`, `useSystemHealth()`, `useKbSources(opts)`, `useKbSearch(query)`, `useKbSource(id)`. Each uses `useQuery`, calls the appropriate axios function from `client.ts`, runs the adapter, and returns the UI shape. Sane staleTimes (15s for status/health, 60s for KB sources).
- [ ] **DoD:** `npx tsc --noEmit` passes. A throwaway test page or `console.log` from a dev session confirms each hook returns the expected UI shape from the live backend.
- [ ] Commit: `feat(web-ui): adapter layer mapping backend responses to design shapes`

### Task 6: Port OPS tab - Hero strip + Server Status + Event Feed + Leaderboard + Encounters + Health Strip

The flagship operator view. Convert `panel-server.jsx` and `panels.jsx` (Hero, EventFeed, Leaderboard, Encounters timeline, HealthStrip) -> TypeScript components. Wire to the React Query hooks from Task 5 + the SSE hook from Task 3.

- [ ] Read `_design-handoff-staging/.../panel-server.jsx` and `_design-handoff-staging/.../panels.jsx` end-to-end.
- [ ] Create `src/components/ops/HeroStrip.tsx` - full-width `var(--bg-2)` strip with server-rack silhouettes flanking stencil "DAYZ NETWORK - OPERATOR PANEL" title + 4-stat marquee (Total Players / Active Encounters / Servers Online / Events Today). Stats pulled from `useServerStatus` + computed counts from event stream.
- [ ] Create `src/components/ops/ServerStatusPanel.tsx` - port `panel-server.jsx` exactly: live UTC clock, uptime, color-coded last-heartbeat (green <2min / amber <5min / red older), animated population gauge, perf cells (tick / FPS / mem%), loaded-mods grid. When backend returns `loaded_mods: null` or `perf: null`, render a "[no data]" empty state in those cells.
- [ ] Create `src/components/ops/EventFeed.tsx` - left column. Filter chips (All / Boss / Players / Server with live counts). Each row = event-type badge (color by category) + server ID + summary + time-ago. Click row to expand JSON payload inline. New events slide-in with amber flash via `.event-row.is-new` (apply via `useLayoutEffect` for one-shot flash). Pause toggle freezes ingestion (already in `useEventStream` hook). Empty state: animated radar sweep + copy "NO SIGNAL - fire an event in-game to see this update."
- [ ] Create `src/components/ops/SidebarTopHunters.tsx` - leaderboard, ranks 1-3 highlighted with podium tints. Pulls from `useLeaderboard()`. When `is_mock: true`, show small "DEMO DATA" chip in panel header.
- [ ] Create `src/components/ops/SidebarRecentEncounters.tsx` - vertical timeline with diamond nodes, mini-avatar + boss icon per row. Pulls from `useRecentEncounters()`. Same `is_mock` chip behavior.
- [ ] Create `src/components/ops/HealthStrip.tsx` - sticky bottom strip, 5 colored dots (Postgres / API / Snapshotter / Embed Q / SSE Bus). Tooltip on hover with `detail` from `useSystemHealth()`. Dots use `.dot-ok` / `.dot-warn` / `.dot-bad` per status.
- [ ] Replace `src/pages-v2/OpsPage.tsx` stub with the real composition: HeroStrip on top, then a 3-row CSS Grid: Row 1 ServerStatusPanel (full width), Row 2 EventFeed (`minmax(0, 1fr)`) + Sidebar (`360px`) containing TopHunters + RecentEncounters, Row 3 HealthStrip (sticky bottom). Min-height 420px on EventFeed.
- [ ] **DoD:** `npx tsc --noEmit` passes. `npm run dev` shows OPS page. Server status panel reflects real `server_01` heartbeat (or "[no data]" if offline). Event feed shows live SSE events sliding in. Leaderboard + encounters render mock data with "DEMO DATA" chip. Health strip dots reflect real backend (`/api/v1/system/health`) - Postgres + API ok/green, Snapshotter status is `fresh` (snapshots ran tonight).
- [ ] Commit: `feat(web-ui): OPS tab - hero, server status, event feed, sidebars, health strip`

### Task 7: Port KNOWLEDGE tab - Browse / Search / Read modes

The KB browser. Convert `panel-kb.jsx` -> TypeScript. Wire to `useKbSources`, `useKbSearch`, `useKbSource` from Task 5. All real data from a 3,396-source corpus.

- [ ] Read `_design-handoff-staging/.../panel-kb.jsx` end-to-end.
- [ ] Create `src/components/kb/KnowledgeSidebar.tsx` - vertical sidebar of source-type icons (book / brackets / play / note / gear). Selecting a type filters the Browse view.
- [ ] Create `src/components/kb/KnowledgeBrowse.tsx` - sources table: title / type / chunks / updated / size. Filterable by source type. Pagination (page_size=50). Each row clickable -> switches to Read view with that source.
- [ ] Create `src/components/kb/KnowledgeSearch.tsx` - large search input (`⌕` glyph). Results list: snippet + source-type pill + relevance score (0-1) shown as a horizontal bar.
- [ ] Create `src/components/kb/KnowledgeRead.tsx` - title + source-type meta header + full content with chunk boundaries highlighted (numbered amber gutters in left margin, faint horizontal rule between chunks). Use `useKbSource(id)` for full content.
- [ ] Add a faint blueprint-grid backdrop (subtle 24px×24px grid lines at ~3% opacity) behind the main content area. CSS-only, no SVG.
- [ ] CREATE / REINDEX buttons visible but stubbed - render as `<button disabled title="// stub: backend write paths not yet wired">CREATE</button>`.
- [ ] Replace `src/pages-v2/KnowledgePage.tsx` stub with the real composition: KnowledgeSidebar (left, fixed width) + tab-switching content area (Browse / Search / Read).
- [ ] **DoD:** `npx tsc --noEmit` passes. `npm run dev` Knowledge tab loads. Browse shows real 3,396 sources from the live corpus, type filter works. Search returns BM25 hits for queries like "OnEntityKilled" or "PlayerBase". Read mode renders a real source's chunks with numbered gutters.
- [ ] Commit: `feat(web-ui): KNOWLEDGE tab - browse, search, read modes against real KB`

### Task 8: Port secondary tabs - SERVERS, PLAYERS, ENCOUNTERS, TROPHIES, ALERTS, SETTINGS

Six tabs from `pages-extra.jsx`. SERVERS + ENCOUNTERS pull real data where available; PLAYERS + TROPHIES + ALERTS are fully mocked (backend has no tables yet - flag clearly with `// MOCK - no backend route yet` and a "DEMO DATA" chip in the panel header). SETTINGS is read-only stubs.

- [ ] Read `_design-handoff-staging/.../pages-extra.jsx` end-to-end. Note the deterministic-by-name avatar shapes in `icons.jsx` `PlayerAvatar` and the `MapSilhouette` component for SERVERS card backdrops.
- [ ] **SERVERS** - `src/pages-v2/ServersPage.tsx` + `src/components/servers/ServerCard.tsx`. 3-col grid of cards. Map silhouette backdrop at ~10% opacity per card (Chernarus / Livonia / Namalsk SVG blobs from `icons.jsx`). Header = server ID + status dot. 2x2 stat grid (Players / Uptime / Active Bosses / Version), population bar, FOCUS / RESTART ghost buttons (stubbed: `disabled`). For now, only `server_01` has real data via `useServerStatus`; render 2 additional mock cards labeled `is_mock: true`.
- [ ] **PLAYERS** - `src/pages-v2/PlayersPage.tsx` + `src/components/players/{PlayerTable,PlayerDrawer,PlayerAvatar}.tsx`. Two-column. Roster table (left, flex 1) + profile drawer (right, 360px). Search bar with `⌕` glyph + filter chips (ALL / ONLINE / FLAGGED). Table cols: avatar / Player (mono, FLAGGED red chip if applicable) / Status / Boss Kills / Hours / Last Seen / Joined. Row click selects -> updates drawer. Drawer: 84px deterministic-by-name avatar, display name (Oswald 22px), Steam ID (mono dimmed), 2x2 stat grid, "Recent Sessions" stub list with amber left-border markers. **Mock data only** - preserve all flavor names from `pages-extra.jsx` verbatim.
- [ ] **ENCOUNTERS** - `src/pages-v2/EncountersPage.tsx` + `src/components/encounters/{TtkHistogram,EncountersTable,BossClassBreakdown}.tsx`. Two-column. Left: TTK Distribution (6-bucket histogram via recharts: 0-50 / 50-100 / 100-150 / 150-200 / 200-250 / 250+ seconds, amber bars w/ glow); All Encounters table (Boss / Killer / Server / TTK / When). Right: Boss Class Breakdown sidebar with silhouette icon + count + amber proportion bar per class. Wire table to `useRecentEncounters(limit=200)`; histogram + breakdown are derived client-side. Falls back to mock when no real kills yet.
- [ ] **TROPHIES** - `src/pages-v2/TrophiesPage.tsx` + `src/components/trophies/TrophyCard.tsx`. 3-col grid. Each card: amber chalice SVG (drop-shadow glow), trophy class name in stencil amber, holder + avatar in mono, "AWARDED Xh AGO - N TRANSFERS" label. Card bg = faint amber -> transparent vertical gradient over `bg-1`. **Mock data only.**
- [ ] **ALERTS** - `src/pages-v2/AlertsPage.tsx` + `src/components/alerts/{AlertRules,RecentFires}.tsx`. Two-column. Left: Alert Rules with `+ NEW RULE` ghost button (stubbed). Each rule = 5-col grid (name+condition / channel / fired-at / on-off toggle / EDIT). Toggle flips local state via `useState`. Disabled rules dim to `var(--fg-4)`. Right: Recent Fires sidebar - 2-line blocks with 2px green left-border accent. **Mock data only.**
- [ ] **SETTINGS** - `src/pages-v2/SettingsPage.tsx`. Single 880px-max panel. Read-only stubs: 5 label/value rows (Backend URL / SSE Endpoint / Postgres / Snapshot interval / Embedding model). Each row: 200px label (uppercase mono) + value field (mono, inset chrome) + hint sub-label below. Bottom: dashed-border "STUB - settings are read-only in this demo" notice. **The Accent Hue picker lives here too - wired in Task 9.**
- [ ] **DoD:** `npx tsc --noEmit` passes. `npm run dev` shows all 6 tabs functional. Real data where applicable (Servers card 1, Encounters table). Mock tabs clearly show "DEMO DATA" chip in panel headers. All flavor names from `pages-extra.jsx` preserved verbatim.
- [ ] Commit: `feat(web-ui): SERVERS, PLAYERS, ENCOUNTERS, TROPHIES, ALERTS, SETTINGS tabs`

### Task 9: Port tweaks panel - runtime hue / density / grain / scanlines

The runtime tweaker is a core delight feature. Convert `tweaks-panel.jsx` -> TypeScript with full hue palette: Blood Rust / Infection Green / Hazmat Yellow / Bruise Violet / Amber Classic. Persist hue + density to localStorage. Wire density / grain / scanline knobs (these survive the prototype-to-prod transition per README).

- [ ] Read `_design-handoff-staging/.../tweaks-panel.jsx` and the `ACCENT_HUES` array in `_design-handoff-staging/.../data.jsx` end-to-end.
- [ ] Create `src/state/tweaks.ts`:
  - Exports `useTweaks()` hook returning `{ hue, density, grain, scanlines, setHue, setDensity, setGrain, setScanlines, resetDefaults }`.
  - Persists to `localStorage` under key `dayz_dash_tweaks_v1`.
  - On change, sets the corresponding CSS variables on `document.documentElement`: `--amber`, `--amber-soft`, `--amber-line` per hue palette; `--density-mult` (0.75 / 1.0 / 1.25); `--grain-opacity` (0-0.20); `--glow-strength` (0-3).
  - Defaults: `hue='blood-rust', density='comfortable', grain=0.06, scanlines=1`.
- [ ] Create `src/components/TweaksPanel.tsx`:
  - Floating panel (top-right, fixed) toggled by a small button or `,` keyboard shortcut.
  - 4 sections: Accent Hue (5 swatches as clickable circles), Density (3 ghost buttons: COMPACT / COMFORT / SPACIOUS), Film Grain (slider 0-20, displaying as 0.00-0.20), CRT Scanlines (slider 0-3 in 0.5 steps).
  - "Reset to defaults" link at the bottom.
- [ ] Mount `<TweaksPanel />` once in `App.tsx` (always rendered, visibility self-managed via internal state).
- [ ] In Task 8's SettingsPage, add the Accent Hue picker as a row (calls into the same `useTweaks()` hook - single source of truth).
- [ ] **DoD:** `npx tsc --noEmit` passes. `npm run dev`: floating tweaks panel toggles open/closed. Switching hue immediately re-tints all amber accents (event flash, dot-live, active tab underline). Density toggle changes paddings ±25% across panels. Grain slider visibly changes film noise. Scanline slider toggles visible CRT lines. Reload preserves hue + density via localStorage; grain + scanlines reset to defaults (per README - they were prototype tuning knobs).
- [ ] Commit: `feat(web-ui): runtime tweaks panel - hue palette, density, grain, scanlines`

### Task 10: Backup + clean - archive legacy src/ to _archive/web-ui-pre-redesign/

The new dashboard is fully built in `src/pages-v2/` + new component subdirs alongside the old `src/pages/{Dashboard,Events,Hive}.tsx`. This task archives the legacy structure and folds `pages-v2/` -> `pages/`.

- [ ] Create `_archive/web-ui-pre-redesign/` directory.
- [ ] Copy (not move yet) the legacy files to archive:
  - `src/pages/Dashboard.tsx`, `Events.tsx`, `Hive.tsx`
  - `src/components/Layout.tsx`, `LoadingSpinner.tsx`, `StatCard.tsx`
  - `src/App.css` (legacy styles)
- [ ] Delete the originals after the copy is verified (`diff -r` between live and archive returns empty for those paths).
- [ ] Rename `src/pages-v2/` -> `src/pages/`. Update all imports across `App.tsx` and any cross-references.
- [ ] Drop `src/App.css` (legacy, no longer imported - verify no `import './App.css'` remains anywhere in the new code).
- [ ] **DoD:** `npx tsc --noEmit` passes. `npm run lint` passes (no unused imports). `npm run dev` still serves all 8 tabs. `_archive/web-ui-pre-redesign/` contains the archived files; `src/` no longer contains the legacy ones.
- [ ] Commit: `chore(web-ui): archive legacy src/ to _archive/web-ui-pre-redesign and consolidate pages/`

### Task 11: Verify - full visual + functional smoke test

End-to-end verification before docs. Run the full app, hit every route, confirm SSE + KB are both live, capture any regressions and fix in this same task.

- [ ] `cd frontends/web-ui && npm run build` - full Vite production build must succeed with zero errors.
- [ ] `cd frontends/web-ui && npm run dev`. Open `http://localhost:6702` (or whichever port Vite picks; default is 5173 - check). All 8 tab URLs reachable: `/ops`, `/servers`, `/players`, `/encounters`, `/trophies`, `/alerts`, `/kb`, `/settings`.
- [ ] Verify the OPS page Server Status panel shows live `server_01` heartbeat (real, not mock - the `is_mock: false` flag on the response).
- [ ] Verify the OPS page Event Feed receives a live SSE event within 2 minutes (the BossSignal mod heartbeat fires every ~30-100s).
- [ ] Verify the KNOWLEDGE tab returns BM25 search hits for `OnEntityKilled` (should return at least 1 result from the real corpus).
- [ ] Verify the SYSTEM HEALTH strip on OPS shows `bosssignal_db: ok`, `kb_db: ok`, `snapshotter: fresh`.
- [ ] Verify the Tweaks panel hue swap visibly retints the dashboard (try Blood Rust -> Hazmat Yellow -> back to Blood Rust).
- [ ] Verify zero console errors in the browser dev tools across all 8 tabs.
- [ ] If ANY of the above fails, fix in this task before committing. Validation commands run before commit.
- [ ] **DoD:** All bullets above pass. The dashboard is demo-ready.
- [ ] Commit: `chore(web-ui): verification pass - all 8 tabs render, SSE + KB live, no console errors`

### Task 12: DASHBOARD-README.md

Document the dashboard for future-you and any collaborator. Per README's DoD bullet.

- [ ] Create `frontends/web-ui/DASHBOARD-README.md` with sections:
  - **What this is** (1 paragraph: operator panel, 8 tabs, real-time SSE)
  - **Run locally** (one-command: `npm install && npm run dev`; assumes BossSignal backend at `:6700`)
  - **Configuration** (`.env` `VITE_API_BASE`, fallback to relative paths)
  - **Tabs at a glance** - table: tab name | route | data source (real vs mock) | notes
  - **Tweaks panel** - what it controls, persistence, where the hue palette is defined
  - **Architecture** - a tiny ASCII diagram (`React Query ← adapters ← axios -> BossSignal :6700`; `EventSource -> useEventStream -> React Query cache`)
  - **Where the design tokens live** (`tailwind.config.js` `theme.extend` + `src/styles/chrome.css`)
  - **Known limitations** - copy from the design README's "Known Issues / Open Follow-ups" section, point to the design's `_design-handoff-staging/` bundle as the canonical reference
  - **How to add a new tab** (5-step recipe - file location, route reg, top-rail entry, keyboard shortcut, page component)
- [ ] **DoD:** File exists, renders cleanly in markdown preview, all referenced commands actually work.
- [ ] Commit: `docs(web-ui): DASHBOARD-README - run, config, tabs, tweaks, architecture`

### Task 13: Final sweep - lint clean + plan handoff doc

Tighten lint to the package.json's actual setting (`--max-warnings 0`), fix any remaining warnings, and write a final handoff summary so the human reading this tomorrow knows exactly what shipped.

- [ ] `cd frontends/web-ui && npm run lint` (with the package.json's actual `--max-warnings 0`). Fix any remaining warnings - most likely candidates: unused imports, unused vars, missing react-hooks deps. Refuse to disable rules; fix the underlying issue.
- [ ] `cd frontends/web-ui && npx tsc --noEmit` final pass.
- [ ] `cd frontends/web-ui && npm run build` final pass.
- [ ] Write `planning/dashboard-build-summary-2026-05-01.md` containing:
  - Tasks completed (1-13 with brief 1-line summary each)
  - Tasks blocked (none, hopefully)
  - Final commit list (`git log --oneline main..HEAD` from the start of this run)
  - Visual description of the final look (no screenshots possible from a CLI run, but a 3-paragraph description: aesthetic, what tabs feel like, what mock vs real looks like)
  - Recommended next session priority (e.g.: bootstrap HiveAPI auth so character sync works, OR: connect-and-kill in-game demo to fire real boss.killed events, OR: wire Trophies/Players/Alerts when their backend tables get added)
- [ ] **DoD:** Lint passes with `--max-warnings 0`. `tsc --noEmit` clean. `npm run build` clean. Summary doc exists. Final commit.
- [ ] Commit: `chore(web-ui): final lint pass + build summary doc`
