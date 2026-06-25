# 02 - Original Intent: reverse-engineered

Best read of what you were trying to build when you wrote `dayzAPI` without knowing the Bohemia stack.

## The elevator pitch you were building toward

> _"A production-grade, multi-tenant, self-hostable SaaS that gives a DayZ server network a shared persistence layer - characters, inventory, and an audit/event stream that all servers in the cluster agree on, with a dashboard, metrics, and first-class Discord/web integration hooks. Drop in a small Enforce mod, point it at the API URL, done."_

That's what the README + ROADMAP + code shape, taken together, are clearly pointing at.

## The architecture you assumed

### Layer 1 - Web backend as the source of truth
Characters and inventory live **in Postgres on your side**. Each DayZ server is a dumb client that reports in and asks "whose character is this what gear do they have" This is the classic **central hive** model from DayZ Mod era (2012-ish), not the current Standalone model. You implicitly rebuilt that mental model.

Key shape:
- `Tenant -> Cluster -> Server -> Player -> Character -> Inventory`
- JWT auth per server on `/v1/auth/server-login`
- Idempotency keys + audit `Event` rows for every mutation
- `MoveTicket` = one-shot, TTL-expiring transfer token. Character is moved by issuing a ticket on server A and redeeming on server B. Very clean, very Stripe-idempotency-key-ish.

### Layer 2 - Inventory sync with conflict detection
The `inventory.apply` endpoint takes an `ops` list + a `base_checksum`. If `base_checksum` doesn't match the server's current checksum, you return a conflict. The client (game server) is expected to re-read and reconcile. This is the same pattern Google Docs / Figma / OT-CRDT systems use. For a game where state is server-authoritative by design, this is overkill but not crazy - it protects against the scenario where two game servers think they own the same character.

### Layer 3 - Enforce mod as a thin RPC client
A PBO that:
1. On mission server init, calls `/v1/auth/server-login` to get a JWT.
2. On `InvokeOnConnect`, calls `/v1/characters/claim` with the steam ID.
3. On a timer, pulls inventory off `PlayerBase`, JSON-encodes it, calls `/v1/inventory/set`.
4. On `InvokeOnDisconnect`, one last `SaveInventory` + `SendHeartbeat`.

Vanilla DayZ persistence (the `.bin` files the engine writes on its own) is assumed to either be turned off or just harmlessly duplicated. You never addressed "what happens when the engine's local persistence and my remote state disagree"

### Layer 4 - Real-time dashboard
SSE stream from `/v1/admin/events/stream` -> React component paints the event log live. Prometheus scrapes `/metrics`. Grafana renders graphs. All standard, all unnecessary for a first mod but nice if the thing actually shipped at scale.

### Layer 5 - Ops / distribution
Docker Compose for local. Render.com for prod. Cloudflare Tunnel so you don't need to open ports on a VPS. `ORIGIN_SECRET` header trick to make sure only traffic coming through your tunnel reaches the origin. This is sound web-ops - the same approach you'd use for a small SaaS.

### Layer 6 - The "eventual parity with DaemonForge" backlog
From `ROADMAP.md`: a second, more generic API surface: `db_objects`, `db_players`, `db_globals`, with save / load / query / update / transaction / increment, and a query DSL that maps a Mongo-ish `$eq/$ne/$in/$and/$or` subset onto Postgres JSONB. That's you reverse-engineering DaemonForge UniversalAPI's MongoDB-backed schema into Postgres. It's actually a sensible _technical_ port - Postgres JSONB can do everything UniversalAPI needs, and it's operationally simpler than MongoDB for solo ops.

## What you were _actually_ solving for (systems-thinking read)

You weren't building "a DayZ mod." You were building **the platform a DayZ server network would sit on top of**, with "the mod" being a thin edge agent. The things you clearly cared about:

1. **Multi-server, single identity.** One player, many servers, one canonical character.
2. **Move between servers with gear.** The `MoveTicket` is the whole value prop.
3. **Server network as a customer.** Multi-tenant from day one = you were imagining hosting this for other people eventually.
4. **Observability and audit.** If anything goes wrong (item dupe, lost gear, transfer exploit), you can forensically replay what happened.
5. **Extensibility as a business moat.** The DaemonForge parity goal means: "any mod that speaks UniversalAPI can point at me instead." You wanted to be a drop-in replacement for existing infrastructure so adoption has zero switching cost.
6. **Operator ergonomics.** Makefile, one-command demo, Render one-click, Cloudflare Tunnel, Dockerized observability. You were de-risking the "I'm a tired server admin at 2am" path before the "does this compile" path.

## What you did NOT solve for (and this is the tell)

- **Anything specific to DayZ as a game.** The API is equally applicable to Rust, ARK, Project Zomboid, 7DTD. There's nothing in here that knows what a `ZmbM_HermitSkinny` or `AKM` is. That's fine - that's the "platform" play - but it means every bit of _game-specific_ value is in the ~500 lines of Enforce that aren't really working.
- **How persistence actually works in DayZ 1.x.** The vanilla engine writes `players.db` (SQLite) + `dynamic_*.bin` files. You have no integration, no intercept, no "I know what the engine just wrote and I'm mirroring it" story. You're running alongside it, not on top of it.
- **Mod signing, key distribution, load order, dependency declarations.** A PBO with no `.bikey`, no `@CF` dependency declaration, no published mod on Workshop. The mod-half was never going to boot on a real server.
- **Bohemia's monetization rules.** Nothing in the code is monetized, but the posture - "multi-tenant SaaS for DayZ server networks" - is exactly the posture Bohemia stares at sideways. You didn't consider that the business shape might be a policy problem.
- **What a target server actually needs.** There's no evidence in the repo that it was shaped around a specific real-world server's pain point. It's a generic platform.

## The honest summary

You built the **backend of DaemonForge UniversalAPI, rebranded as a hive, with an opinionated web ops story and a React admin UI**, paired with a half-fictional Enforce client that was written against an imagined REST API shape that partially exists in the real Enfusion engine.

The architecture is not dumb. It's actually a reasonable design for "external data service for modded DayZ server networks." The problems are:
1. It duplicates something that already exists and is adopted (UniversalAPI), without a differentiator the scene cares about.
2. The Enforce half - where 100% of the actual DayZ-specific value has to live - was written blind and is not a running mod.
3. The "Hive" framing invites exactly the kind of attention from Bohemia and the community that a small project wants to avoid.

Covered in depth in `03-what-was-broken.md`.
