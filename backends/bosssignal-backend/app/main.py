"""
BossSignal backend — FastAPI entry point.

Stripped from dayzAPI:
  ✗ Tenant / Cluster multi-tenancy
  ✗ Character claim / heartbeat
  ✗ Inventory sync / conflict detection
  ✗ MoveTicket hive transfers
  ✗ JWT auth (replaced with shared-secret header)
  ✗ CORS allow_origins=["*"] + allow_credentials=True

Kept + reworked:
  ✓ Events table (append-only log)
  ✓ SSE live stream
  ✓ Prometheus middleware (optional)
  ✓ Idempotency key deduplication
  ✓ Async SQLAlchemy + asyncpg

Serves the React production dashboard from `dashboard/` (volume-mounted
from frontends/web-ui/dist via docker-compose). SPA fallback catches
client-side routes (/ops, /servers, /kb, ...) and returns index.html.
Falls back gracefully if the dashboard hasn't been built yet — serves
a placeholder explaining how to build it.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db.database import create_tables
from app.routers import bosses, dashboard, events, hive, kb, trophies

log = logging.getLogger(__name__)
settings = get_settings()

# ── Dashboard mount config ────────────────────────────────────────────────────
# Volume-mounted via docker-compose: ../../frontends/web-ui/dist -> /app/dashboard
DASHBOARD_DIR = Path("dashboard")
if not DASHBOARD_DIR.exists() or not (DASHBOARD_DIR / "index.html").is_file():
    cand = Path("../../frontends/web-ui/dist")
    if cand.exists() and (cand / "index.html").is_file():
        DASHBOARD_DIR = cand

DASHBOARD_INDEX = DASHBOARD_DIR / "index.html"
DASHBOARD_ASSETS = DASHBOARD_DIR / "assets"



# ── Lifespan: create tables on startup ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    if not DASHBOARD_INDEX.is_file():
        log.warning(
            "Dashboard not found at %s. Build it with: "
            "cd frontends/web-ui && npm run build",
            DASHBOARD_INDEX,
        )
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="BossSignal",
    description=(
        "Boss encounter telemetry for DayZ server networks. "
        "Receives structured events from the Enforce mod, "
        "stores them, and streams them live to the dashboard."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)


# ── CORS ──────────────────────────────────────────────────────────────────────
# Origins are env-driven (CORS_ORIGINS, comma-separated). Default "*" is for local
# dev; set an explicit origin list in production. Per the CORS spec, credentials
# cannot be combined with a wildcard origin, so we only enable them for a fixed list.
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
_allow_any_origin = "*" in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_any_origin else _cors_origins,
    allow_credentials=not _allow_any_origin,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers (registered FIRST so API routes win over the SPA fallback) ──────
app.include_router(events.router)
app.include_router(bosses.router)
app.include_router(trophies.router)
app.include_router(dashboard.router)
app.include_router(hive.router)
app.include_router(kb.router)


# ── Health (registered before SPA fallback) ──────────────────────────────────
@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ── Legacy static (kept for backward compat — old dashboard.html still at /static/dashboard.html) ──
app.mount("/static", StaticFiles(directory="static"), name="static_legacy")


# ── Dashboard assets (Vite outputs JS/CSS into dist/assets/) ────────────────
# Only mount if the directory exists at startup. If absent, the SPA fallback
# below renders a friendly placeholder explaining how to build.
if DASHBOARD_ASSETS.is_dir():
    app.mount("/assets", StaticFiles(directory=str(DASHBOARD_ASSETS)), name="dashboard_assets")
elif Path("../../frontends/web-ui/dist/assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(Path("../../frontends/web-ui/dist/assets"))), name="dashboard_assets")



# ── SPA fallback (last route registered — catches /, /ops, /servers, etc.) ──
PLACEHOLDER_HTML = """<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><title>BossSignal</title>
<style>
  body{margin:0;background:#0d0f0e;color:#d8d6c8;font:14px/1.5 ui-sans-serif,system-ui,sans-serif;padding:48px;min-height:100vh}
  h1{font-family:Oswald,sans-serif;letter-spacing:.18em;font-size:22px;color:#d97e2b}
  code{background:#1a1c1b;padding:2px 6px;border:1px solid #2a2c2a;font-family:ui-monospace,monospace}
  a{color:#d97e2b}
</style></head>
<body>
  <h1>DASHBOARD NOT BUILT YET</h1>
  <p>The React dashboard hasn't been built. Run:</p>
  <pre><code>cd frontends/web-ui &amp;&amp; npm install &amp;&amp; npm run build</code></pre>
  <p>Then restart this backend (<code>docker compose up -d --build</code>) and reload.</p>
  <hr style="border:none;border-top:1px solid #2a2c2a;margin:24px 0">
  <p>Backend API is live: <a href="/docs">Swagger</a> · <a href="/health">/health</a> ·
     <a href="/api/v1/system/health">/api/v1/system/health</a></p>
  <p>Legacy single-file dashboard: <a href="/static/dashboard.html">/static/dashboard.html</a></p>
</body></html>
"""


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """
    SPA catch-all. Serves dist/index.html for any non-API route so client-side
    React Router handles /ops, /servers, /kb, etc.

    Order: API routes (registered above) match first; this only fires for
    paths that no router/handler claimed.
    """
    if not DASHBOARD_INDEX.is_file():
        return HTMLResponse(PLACEHOLDER_HTML, status_code=200)

    # If the path resolves to a real file inside dist (favicon.ico, vite.svg,
    # etc.), serve it directly. Otherwise, return index.html for SPA routing.
    if full_path:
        candidate = DASHBOARD_DIR / full_path
        # Defensive: refuse path traversal — resolve must stay inside DASHBOARD_DIR
        try:
            resolved = candidate.resolve()
            base = DASHBOARD_DIR.resolve()
            if base in resolved.parents and resolved.is_file():
                return FileResponse(resolved)
        except (OSError, ValueError):
            pass

    return FileResponse(DASHBOARD_INDEX)
