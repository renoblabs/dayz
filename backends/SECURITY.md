# Security

This document describes the authentication and authorization model now in force for
the two backend services in this directory:

- **HiveAPI** (`backends/hiveapi`) — cross-server character/inventory hive for DayZ.
- **BossSignal** (`backends/bosssignal-backend`) — boss-encounter telemetry + dashboard.

It is meant to be honest about what is and is not protected. Read the
[Operator requirements](#operator-requirements-read-this-before-deploying) section
before any non-local deployment.

---

## HiveAPI

### Authentication model

HiveAPI uses a two-tier model: a **server identity token** for game servers and
**HTTP Basic** for human administrators.

#### Server tokens (Bearer JWT)

1. A game server calls `POST /server-login` with its `server_id` and a `proof`
   (a base64 RSA PKCS#1 v1.5 / SHA-256 signature over the `server_id`, verified
   against the server's stored `public_key_pem`).
2. On a valid proof, HiveAPI issues a short-lived JWT signed **HS256** with
   `JWT_SIGNING_SECRET`. The token carries `sub` (the server id), `iss`, `exp`,
   and a `type`/`cluster` claim. Default lifetime is `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
   (60 minutes).
3. Every state-changing endpoint depends on `get_authenticated_server_id`
   (`app/deps.py`), which verifies the Bearer token against `JWT_SIGNING_SECRET`
   using `JWT_ALGORITHM` (HS256), **requires** the `exp`, `iss`, and `sub` claims,
   and returns the authenticated `server_id` from the `sub` claim.

This authenticated `server_id` is the **only** trusted source of caller identity.
State-changing endpoints derive ownership from it server-side; `server_id` is **not**
read from request bodies. Requests with a missing/malformed token get `401`; if no
signing secret is configured the dependency fails closed with `503`.

#### Dev-only login shortcut

`POST /server-login` has a no-proof shortcut that skips RSA verification and issues a
token directly. It is gated on **both** `REQUEST_SIGNATURE_REQUIRED` being `False`
**and** `ENV` being `dev` or `test`. In production (`ENV=production`) the proof
signature is always required, even if `REQUEST_SIGNATURE_REQUIRED` is misconfigured
to `False`. The shortcut logs a warning when used.

#### Admin endpoints (HTTP Basic)

Admin routes depend on `require_admin` (`app/deps.py`), which enforces HTTP Basic
against `ADMIN_USERNAME` / `ADMIN_PASSWORD` using a constant-time comparison
(`secrets.compare_digest`). It **fails closed**: if `ADMIN_PASSWORD` is unset, admin
access is disabled (`403`), never silently open. Bad credentials return `401`.

### Integration status — WIP

HiveAPI's end-to-end server↔mod integration is **not finished**. The in-game Enforce
mod does **not yet perform proof signing**, so the production RSA-proof login path has
not been exercised by a real client. Today the working path is the dev/test no-proof
shortcut. Treat HiveAPI auth as implemented-but-unproven against a live mod until that
loop is closed.

### Relevant settings (`app/config.py`)

| Setting | Default | Notes |
| --- | --- | --- |
| `ENV` | `dev` | `dev` / `test` / `production`. Insecure shortcuts honored only in `dev`/`test`. |
| `JWT_SIGNING_SECRET` | _unset_ | **Required** to issue or verify tokens. Unset ⇒ login `503`, auth dependency `503`. |
| `JWT_ALGORITHM` | `HS256` | Symmetric; sign and verify both use `JWT_SIGNING_SECRET`. |
| `JWT_ISSUER` | `hiveapi` | Enforced as the `iss` claim on verify. |
| `REQUEST_SIGNATURE_REQUIRED` | `True` | Leave `True` in production. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / _empty_ | Empty password disables admin (`403`). |
| `CORS_ORIGINS` | `*` | Set explicit origins in production; credentials are auto-disabled when `*`. |

---

## BossSignal

### Authentication model

BossSignal splits routes into **write** (ingest from game servers) and **read**
(dashboard / queries).

#### Write path — shared secret

`POST /api/v1/events` and the `/api/v1/hive/*` lookups require the
`X-BossSignal-Secret` request header. The secret is compared against
`BOSSSIGNAL_SECRET` using a constant-time comparison (`secrets.compare_digest`), and
is accepted **only** via the header — never from the URL query string (query params
leak into access logs, proxies, and browser history). While `BOSSSIGNAL_SECRET` is
left at its `CHANGE_ME` placeholder, every secret-checked request is refused with
`503`. A wrong/missing secret returns `401`. This secret must match
`BossSignalConfig.SHARED_SECRET` in the Enforce mod.

#### Read path — open by default

Read endpoints (dashboard, `/api/v1/bosses`, `/api/v1/servers`, trophies, KB, and the
SSE event stream) are **open by default** so the local browser dashboard works without
a secret. This is a deliberate choice for the intended local/single-operator
deployment, not an oversight — but it does mean that, by default, anyone who can reach
the read endpoints can read telemetry.

Setting `REQUIRE_READ_AUTH=true` additionally requires the `X-BossSignal-Secret`
header on those read routes (defence-in-depth, e.g. when the dashboard sits behind its
own auth). The write path always requires the secret regardless of this flag.

### Relevant settings (`app/config.py`)

| Setting | Default | Notes |
| --- | --- | --- |
| `BOSSSIGNAL_SECRET` | `CHANGE_ME` | **Required**; placeholder ⇒ secret-checked routes return `503`. Must match the mod. |
| `REQUIRE_READ_AUTH` | `False` | `True` ⇒ read routes also require `X-BossSignal-Secret`. |
| `CORS_ORIGINS` | `*` | Set explicit origins in production; credentials auto-disabled when `*`. |
| `DEBUG` | `False` | Keep `False` in production (disables SQL echo / verbose logging). |

---

## Operator requirements — read this before deploying

The defaults are tuned for **local development**. Before any non-local deployment you
**must**:

- Set **`JWT_SIGNING_SECRET`** (HiveAPI) to a strong random value
  (e.g. `openssl rand -hex 32`). Without it, HiveAPI cannot issue or verify tokens.
- Set **`ADMIN_PASSWORD`** (HiveAPI). An empty password disables admin endpoints
  entirely (fail-closed), so admin functionality will not work until you set it.
- Set **`BOSSSIGNAL_SECRET`** (BossSignal) to a strong random value matching the
  Enforce mod's `SHARED_SECRET`. The placeholder blocks all secret-checked routes.
- Set **`ENV=production`** (HiveAPI) so the dev no-proof login shortcut is disabled.
- Set explicit **`CORS_ORIGINS`** on both services instead of the `*` default.
- Serve both services over **TLS** (terminate at a reverse proxy or tunnel). Bearer
  tokens and shared secrets are sent in headers and must not traverse plaintext HTTP.
- Consider **`REQUIRE_READ_AUTH=true`** for BossSignal if the read dashboard should not
  be world-readable.

This is not a security guarantee. It documents the controls that exist; it does not
claim the services have been audited or penetration-tested.

---

## Reporting a vulnerability

If you discover a security issue in either backend, please report it **privately** —
do not open a public GitHub issue or PR that includes exploit details. Contact the
repository owner directly (e.g. via the email on the GitHub profile, or a private
security advisory) with a description, reproduction steps, and the affected
endpoint(s)/version. These are hobby/personal-project backends maintained on a
best-effort basis, so please allow reasonable time for a response before any public
disclosure. Thank you for disclosing responsibly.
