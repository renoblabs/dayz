# DayZ Ops Dashboard

The dashboard for the DayZ telemetry stack - single-operator admin view across **8 top-rail tabs**: OPS - SERVERS - PLAYERS - ENCOUNTERS - TROPHIES - ALERTS - KNOWLEDGE - SETTINGS. Industrial / military / amber-on-gunmetal aesthetic ("blood rust on infection green"). Live event feed via SSE, real-time server status, full-text search across the 3,396-source knowledge base, runtime tweaks panel.

## Two ways to run

### Dev mode (Vite hot-reload, recommended for development)

```bash
cd frontends/web-ui
npm install
npm run dev      # http://localhost:5173 (Vite dev server)
```

Hits the BossSignal backend on `:6700` via `VITE_API_BASE` (configured in `.env`).
Hot-module reload, fast iteration.

### Production mode (one-tunnel, recommended for a single public URL)

```bash
# 1. Build the dashboard
cd frontends/web-ui
npm run build      # outputs to ./dist/

# 2. Restart the BossSignal backend (picks up the dist/ via volume mount)
cd ../../backends/bosssignal-backend
docker compose up -d --build      # only first time after main.py / compose changes
# (subsequent rebuilds: just `npm run build` - dist is volume-mounted, no docker restart needed)

# 3. The dashboard is now served from the BossSignal backend itself:
#    http://localhost:6700/        -> React dashboard (SPA)
#    http://localhost:6700/api/v1/ -> API
#    http://localhost:6700/static/dashboard.html -> legacy single-file dashboard (kept for backward compat)
#    http://localhost:6700/health  -> backend health
#    http://localhost:6700/docs    -> OpenAPI Swagger
```

The FastAPI app mounts `/assets` -> `frontends/web-ui/dist/assets/` and registers an SPA fallback (`/{full_path:path}`) that serves `dist/index.html` for any non-API path. Client-side routes (`/ops`, `/servers`, `/kb`, etc.) all resolve to the React app, with React Router handling the routing browser-side. Path-traversal-guarded so static files inside `dist/` (favicon, etc.) serve directly.

If `dist/` is missing, the backend serves a friendly placeholder explaining how to build it.

### Public access via tunnel

Production mode + a public tunnel (e.g. ngrok) = a single URL works for the dashboard AND the API:

```
https://your-tunnel.ngrok-free.app/         -> dashboard
https://your-tunnel.ngrok-free.app/ops      -> OPS tab (SPA)
https://your-tunnel.ngrok-free.app/api/v1/system/health -> API
```

ngrok free-tier shows a one-time interstitial per browser session ("Click to visit site"). To run a tunnel: `ngrok http 6700` and use the hostname it prints in place of `your-tunnel.ngrok-free.app`.

### Backend dependencies

Running BossSignal backend at `:6700` is required for both modes. To bring it up if not running:

```bash
cd backends/bosssignal-backend
docker compose up -d
```

For real KB data (sources / search / read views): also start the platform postgres:

```bash
docker start dayz-stack-postgres
```

## Configuration

```bash
# .env (gitignored - copy from .env.example to start)
VITE_API_BASE=http://127.0.0.1:6700
```

If unset, the dashboard uses relative paths and assumes same-origin deployment (e.g. served from BossSignal backend or behind a reverse tunnel).

## Tabs at a glance

| Tab | Route | Data | Notes |
|---|---|---|---|
| **OPS** | `/ops` | mostly real | Hero strip + Server Status (real for `server_01`) + live SSE Event Feed + Top Hunters (mock unless real kills exist) + Recent Encounters (mock unless real kills) + Health Strip (real). |
| **SERVERS** | `/servers` | mixed | Card 1 = real `server_01`; cards 2-3 = mock (`tisy_hermit` Livonia, `Coast_Bambi` Namalsk). FOCUS / RESTART buttons are stubbed. |
| **PLAYERS** | `/players` | mock | 10 mock players with realistic Steam handles. Backend has no players table yet - wire post-demo. |
| **ENCOUNTERS** | `/encounters` | mixed | TTK histogram + table from real `boss_encounters` (mock data when empty); Boss Class Breakdown sidebar derived client-side. |
| **TROPHIES** | `/trophies` | mock | 6 mock trophies. Backend trophies table is wired but may be empty; real rows appear once `trophy.awarded` events exist. |
| **ALERTS** | `/alerts` | mock | 5 mock rules + 4 mock fires. No backend alerts table yet. ON/OFF toggles are local state only. |
| **KNOWLEDGE** | `/kb` | **all real** | Browse 3,396 sources (paginated 50/page, filterable by 7 source_types) - Search via BM25 over the chunks corpus - Read view shows full source with chunk boundaries highlighted. |
| **SETTINGS** | `/settings` | read-only stub | Backend URL / SSE Endpoint / Postgres / Snapshot interval / Embedding model + Accent Hue picker (single source of truth shared with TweaksPanel). |

Every panel that renders mock data shows a small amber **DEMO** chip in the panel header.

## Tweaks panel

Floating bottom-right "◧ TWEAKS" button toggles a panel with four knobs:

- **Accent Hue** - Blood Rust (default) - Infection Green - Hazmat Yellow - Bruise Violet - Amber Classic.
- **Density** - compact / comfortable / spacious. Sets `--density-mult` (0.75 / 1.0 / 1.25) on `<html>`; panels can opt-in by referencing the variable.
- **Film grain** - 0-20% (sets `--grain-opacity` on root, the body::before grain layer reads it).
- **CRT scanlines** - 0-3 (sets `--glow-strength` for `.live-region::after` and `.crt-overlay`).

Persistence: hue + density survive page reload via `localStorage` key `dayz_dash_tweaks_v1`. Grain + scanlines reset to defaults each session - by design, they were prototype tuning knobs and the chosen defaults (0.06 / 1) ship as fixed.

The same hook (`useTweaks()`) backs the Settings page's Accent Hue picker.

## Architecture

```
                    ┌--------------┐
                    |  TopRail     |  ← brand mark, 8 nav tabs (NavLink),
                    |              |     SSE dot, pause/resume, UTC clock
                    `------┬-------┘
                           |
   ┌-----------------------┼---------------------┐
   |                       ▼                     |
   |             EventStreamProvider             |
   |  (single useEventStream -> /api/v1/events/stream)
   |              ↓ React Query cache: ['events','stream']
   |                                             |
   ▼                       |                     ▼
useDashboardData hooks     |            useSharedEventStream()
  ↓ React Query            |                     |
  ↓ adapters.ts            |                     |
  ↓ apiClient (axios)      |                     |
  ↓ /api/v1/* (BossSignal :6700)                 |
  -> useServerStatus, useLeaderboard,             |
    useRecentEncounters, useSystemHealth,        |
    useKbSources, useKbSearch, useKbSource       |
                                                 |
                               ┌-----------------┴--------------┐
                               ▼                                ▼
                       Routes: 8 pages                    EventFeed
                       OPS / SERVERS / etc.               (rows + filters)
```

Key constraint: **only ONE EventSource connection** is opened, owned by `EventStreamProvider`. Every consumer (TopRail, OpsPage, EventFeed, HeroStrip, HealthStrip) reads via `useSharedEventStream()`.

## Where the design tokens live

- Color / font / radius / spacing tokens - `tailwind.config.js` `theme.extend` (oklch values direct from the design's `styles.css`).
- Same tokens as CSS custom properties on `:root` - `src/index.css`. The Tweaks panel mutates these at runtime (`document.documentElement.style.setProperty`).
- Panel chrome utilities (`.panel`, `.tick-corners`, `.dot.live`, `.bar-track`, `.event-row.fresh` slide-in, `.toprail`, `.hero-strip`, `.healthstrip`, `.blueprint-bg`, `.radar-sweep`, `.demo-chip`) - `src/styles/chrome.css`, imported above `@tailwind` directives.

The README's hex-code color block in `_design-handoff-staging/.../README.md` is **stale** - the actual palette is the oklch values in `styles.css`. When in doubt, `styles.css` wins.

## Known limitations

1. **Responsive - minimal pass shipped.** Desktop-primary by design. Mobile (<900px) gets the **minimum** to not visually break: top-rail tabs scroll horizontally; 2-col page grids (OPS row 2, PLAYERS, ENCOUNTERS, ALERTS) stack vertically via `.stack-on-mobile` utility class; health strip scrolls horizontally; brand subtitle + search hint hidden on narrow screens. Tables in PLAYERS / ENCOUNTERS still benefit from horizontal scroll on phones - that's intentional, not redesigned. Hamburger menu, fluid hero stats, etc. are deferred post-demo.
2. **`` help overlay** - listed in keyboard shortcuts but not implemented.
3. **`/` focus dispatch** - works on Players + KB Search; other pages ignore the event because there's no input to focus.
4. **Trophies / Alerts / Players** are fully mocked. Backend has no tables for these yet - ship the demo with mocks, wire post-demo.
5. **CREATE / REINDEX (Knowledge)** and **+ NEW RULE / EDIT (Alerts)** and **FOCUS / RESTART (Servers)** are visibly disabled stubs labeled `// stub`. Backend write paths aren't wired.
6. **Hero strip + server-card backdrops** are rendered as SVG silhouettes. They're designed as swap targets for ComfyUI-generated PNGs later - drop them in via CSS `background-image` on `.hero-strip` and `.server-card-bg` selectors. Keep the SVG silhouettes as fallbacks.

The original design reference bundle is staged at `_design-handoff-staging/design_handoff_dayz_ops_dashboard/` - that's the canonical source of truth for visual fidelity decisions.

## How to add a new tab

1. **Create the page component**: `src/pages/MyTabPage.tsx` returning a `<main>` with `.panel.tick-corners` chrome.
2. **Register the route** in `src/App.tsx`: `<Route path="/my-tab" element={<MyTabPage />} />`.
3. **Add the top-rail entry** in `src/components/TopRail.tsx`: append to the `TABS` array.
4. **Wire the keyboard shortcut** in `src/hooks/useGlobalShortcuts.ts`: add `<letter>: '/my-tab'` to the `ROUTES` map.
5. **(If wiring real data)** Add an axios method to `src/api/client.ts`, an adapter in `src/api/adapters.ts`, and a typed React Query hook in `src/hooks/useDashboardData.ts`. The existing patterns are short enough to copy.

## Where things are

| Concern | File |
|---|---|
| Routes + Shell | `src/App.tsx` |
| Top rail | `src/components/TopRail.tsx` |
| Tweaks panel | `src/components/TweaksPanel.tsx` + `src/state/tweaks.ts` |
| SSE | `src/hooks/useEventStream.ts` + `src/hooks/eventStreamContext.tsx` |
| Keyboard shortcuts | `src/hooks/useGlobalShortcuts.ts` |
| Backend client | `src/api/client.ts` |
| API -> UI adapters | `src/api/adapters.ts` |
| React Query hooks | `src/hooks/useDashboardData.ts` |
| Types | `src/types/index.ts` |
| Mock flavor data | `src/lib/mockData.ts` |
| Format utils | `src/lib/format.ts` |
| Icons (boss / event / map / avatar) | `src/components/icons.tsx` |
| Design tokens (Tailwind) | `tailwind.config.js` |
| Design tokens (CSS vars) | `src/index.css` |
| Custom chrome utilities | `src/styles/chrome.css` |
| 8 page components | `src/pages/{Ops,Servers,Players,Encounters,Trophies,Alerts,Knowledge,Settings}Page.tsx` |
| OPS sub-components | `src/components/ops/*.tsx` |
| KB sub-components | `src/components/kb/*.tsx` |
