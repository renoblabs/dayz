/* ─────────────────────────────────────────────────────────────────
   adapters — map raw BossSignal API responses to UI shapes panels
   consume. Pure functions; safe defaults for missing fields.
   ───────────────────────────────────────────────────────────────── */

import type {
  ServerStatus,
  ServerStatusUI,
  EventUI,
  LeaderboardUI,
  LeaderboardEntryUI,
  EncountersUI,
  EncounterUI,
  KbSourcesPageUI,
  KbSourceUI,
  KbSearchUI,
  KbSearchHitUI,
  KbSourceDetailUI,
  KbChunkUI,
  SystemHealthUI,
  PlayerUI,
  TrophyUI,
  GlobalStatsUI,
  AlertRuleUI,
  AlertHistoryUI,
} from '../types'

type Raw = Record<string, unknown>

function asString(v: unknown, dflt = ''): string {
  return typeof v === 'string' ? v : dflt
}
function asStringOrNull(v: unknown): string | null {
  return typeof v === 'string' ? v : null
}
function asNumber(v: unknown, dflt = 0): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : dflt
}
function asNumberOrNull(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}
function asBool(v: unknown, dflt = false): boolean {
  return typeof v === 'boolean' ? v : dflt
}
function asArray<T = unknown>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : []
}
function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {}
}

// ─── Server status ──────────────────────────────────────────────
export function adaptServerStatus(raw: Raw | ServerStatus | null | undefined): ServerStatusUI {
  const r: Raw = (raw ?? {}) as Raw
  const serverId = asString(r['server_id'], 'server_01')
  return {
    server_id:           serverId,
    name:                asString(r['name'], serverId), // backend has no .name yet — fall back
    map:                 (asString(r['map'], '') as ServerStatusUI['map']) || null,
    player_count:        asNumber(r['player_count']),
    player_max:          asNumberOrNull(r['player_max']),
    uptime_seconds:      asNumberOrNull(r['uptime_seconds']),
    last_heartbeat:      asStringOrNull(r['last_heartbeat']) ?? asStringOrNull(r['last_seen']),
    bosssignal_version:  asStringOrNull(r['bosssignal_version']),
    loaded_mods:         (r['loaded_mods'] && Array.isArray(r['loaded_mods'])) ? (r['loaded_mods'] as ServerStatusUI['loaded_mods']) : null,
    perf:                (r['perf'] && typeof r['perf'] === 'object') ? (r['perf'] as ServerStatusUI['perf']) : null,
    is_online:           asBool(r['is_online']),
    active_boss_count:   asNumber(r['active_boss_count']),
    active_bosses:       asArray(r['active_bosses']) as ServerStatusUI['active_bosses'],
    is_mock:             asBool(r['is_mock']),
  }
}

// ─── Event (SSE/REST) ───────────────────────────────────────────
export function adaptEvent(raw: Raw): EventUI {
  return {
    id:          asString(raw['id']),
    event_type:  asString(raw['event_type']),
    server_id:   asString(raw['server_id']),
    received_at: asString(raw['received_at']),
    data:        asRecord(raw['data']),
  }
}

// ─── Leaderboard ────────────────────────────────────────────────
export function adaptLeaderboard(raw: Raw | null | undefined): LeaderboardUI {
  const r = (raw ?? {}) as Raw
  const rows = asArray<Raw>(r['rows']).map(adaptLeaderboardEntry)
  return {
    window_days: asNumber(r['window_days'], 7),
    rows,
    is_mock:     asBool(r['is_mock']),
  }
}
function adaptLeaderboardEntry(raw: Raw): LeaderboardEntryUI {
  return {
    rank:              asNumber(raw['rank']),
    player_id:         asString(raw['player_id']),
    player_name:       asString(raw['player_name']),
    boss_kills:        asNumber(raw['boss_kills']),
    fastest_kill_sec:  asNumberOrNull(raw['fastest_kill_sec']),
    favorite_boss:     typeof raw['favorite_boss']    === 'string' ? raw['favorite_boss'] as string : undefined,
    favorite_weapon:   typeof raw['favorite_weapon']  === 'string' ? raw['favorite_weapon'] as string : undefined,
    is_mock:           asBool(raw['is_mock']),
  }
}

// ─── Encounters ─────────────────────────────────────────────────
export function adaptEncounters(raw: Raw | null | undefined): EncountersUI {
  const r = (raw ?? {}) as Raw
  return {
    items:   asArray<Raw>(r['items']).map(adaptEncounter),
    is_mock: asBool(r['is_mock']),
  }
}
function adaptEncounter(raw: Raw): EncounterUI {
  return {
    id:                    asString(raw['id']),
    server_id:             asString(raw['server_id']),
    boss_id:               asString(raw['boss_id']),
    boss_type:             asString(raw['boss_type']),
    display_name:          asString(raw['display_name'], asString(raw['boss_type'])),
    spawned_at:            asStringOrNull(raw['spawned_at']),
    killed_at:             asStringOrNull(raw['killed_at']),
    time_to_kill_seconds:  asNumberOrNull(raw['time_to_kill_seconds']),
    killer_player_id:      asStringOrNull(raw['killer_player_id']),
    killer_player_name:    asStringOrNull(raw['killer_player_name']),
    killer_weapon:         asStringOrNull(raw['killer_weapon']),
    player_count_at_spawn: asNumberOrNull(raw['player_count_at_spawn']),
    status:                asString(raw['status'], 'unknown'),
    is_mock:               asBool(raw['is_mock']),
  }
}

// ─── KB sources list ────────────────────────────────────────────
export function adaptKbSources(raw: Raw | null | undefined): KbSourcesPageUI {
  const r = (raw ?? {}) as Raw
  return {
    kb_available: asBool(r['kb_available']),
    page:         asNumber(r['page'], 1),
    page_size:    asNumber(r['page_size'], 50),
    total:        asNumber(r['total']),
    items:        asArray<Raw>(r['items']).map(adaptKbSource),
  }
}
function adaptKbSource(raw: Raw): KbSourceUI {
  return {
    id:          asString(raw['id']),
    url:         asString(raw['url']),
    source_type: asString(raw['source_type']),
    title:       asStringOrNull(raw['title']),
    rel_path:    asStringOrNull(raw['rel_path']),
    sub_kind:    asStringOrNull(raw['sub_kind']),
    text_len:    asNumberOrNull(raw['text_len']),
    fetched_at:  asStringOrNull(raw['fetched_at']),
  }
}

// ─── KB search ──────────────────────────────────────────────────
export function adaptKbSearch(raw: Raw | null | undefined): KbSearchUI {
  const r = (raw ?? {}) as Raw
  return {
    kb_available: asBool(r['kb_available']),
    query:        asString(r['query']),
    limit:        asNumber(r['limit'], 15),
    items:        asArray<Raw>(r['items']).map(adaptKbSearchHit),
  }
}
function adaptKbSearchHit(raw: Raw): KbSearchHitUI {
  return {
    chunk_id:    asString(raw['chunk_id']),
    source_id:   asString(raw['source_id']),
    chunk_index: asNumber(raw['chunk_index']),
    snippet:     asString(raw['snippet']),
    source_url:  asString(raw['source_url']),
    source_type: asString(raw['source_type']),
    title:       asStringOrNull(raw['title']),
    score:       asNumber(raw['score']),
  }
}

// ─── KB single source + chunks ──────────────────────────────────
export function adaptKbSourceDetail(raw: Raw | null | undefined): KbSourceDetailUI {
  const r = (raw ?? {}) as Raw
  const src = r['source']
  let source: KbSourceDetailUI['source'] = null
  if (src && typeof src === 'object') {
    const s = src as Raw
    source = {
      ...adaptKbSource(s),
      content_hash: asString(s['content_hash']),
      raw_len:      asNumber(s['raw_len']),
      cleaned_len:  asNumber(s['cleaned_len']),
      metadata:     asRecord(s['metadata']),
    }
  }
  return {
    kb_available: asBool(r['kb_available']),
    source,
    chunks:       asArray<Raw>(r['chunks']).map(adaptKbChunk),
    chunk_count:  asNumber(r['chunk_count']),
  }
}
function adaptKbChunk(raw: Raw): KbChunkUI {
  return {
    id:            asString(raw['id']),
    chunk_index:   asNumber(raw['chunk_index']),
    text:          asString(raw['text']),
    metadata:      asRecord(raw['metadata']),
    has_embedding: asBool(raw['has_embedding']),
  }
}

// ─── System health ──────────────────────────────────────────────
export function adaptSystemHealth(raw: Raw | null | undefined): SystemHealthUI {
  const r = (raw ?? {}) as Raw
  const bs = asRecord(r['bosssignal_db'])
  const kb = asRecord(r['kb_db'])
  const corpus = asRecord(r['kb_corpus'])
  const snap = asRecord(r['snapshotter'])
  return {
    bosssignal_db: { status: asString(bs['status'], 'unknown'), detail: asStringOrNull(bs['detail']) },
    kb_db:         { status: asString(kb['status'], 'unknown'), detail: asStringOrNull(kb['detail']) },
    kb_corpus: {
      sources:       asNumberOrNull(corpus['sources']) ?? undefined,
      chunks:        asNumberOrNull(corpus['chunks']) ?? undefined,
      embedded:      asNumberOrNull(corpus['embedded']) ?? undefined,
      embed_percent: asNumberOrNull(corpus['embed_percent']) ?? undefined,
    },
    snapshotter: {
      status:        asString(snap['status'], 'unknown'),
      last_capture:  asStringOrNull(snap['last_capture']),
      age_hours:     asNumberOrNull(snap['age_hours']),
      days_banked:   asNumberOrNull(snap['days_banked']),
      total_rows:    asNumberOrNull(snap['total_rows']),
      detail:        asStringOrNull(snap['detail']),
    },
    checked_at: asString(r['checked_at']),
  }
}

// ─── Players ──────────────────────────────────────────────────
export function adaptPlayers(raw: unknown): PlayerUI[] {
  return asArray<Raw>(raw).map(r => ({
    steam_id:          asString(r['steam_id']),
    name:              asString(r['name']),
    status:            asString(r['status'], 'offline'),
    boss_kills:        asNumber(r['boss_kills']),
    hours:             asNumber(r['hours']),
    last_seen:         asString(r['last_seen']),
    joined_at:         asString(r['joined_at']),
    flagged:           asBool(r['flagged']),
    current_server_id: asStringOrNull(r['current_server_id']),
  }))
}

// ─── Trophies ─────────────────────────────────────────────────
export function adaptTrophies(raw: unknown): TrophyUI[] {
  return asArray<Raw>(raw).map(r => ({
    id:             asString(r['id']),
    trophy_class:   asString(r['trophy_class']),
    boss_type:      asString(r['boss_type']),
    holder_id:      asStringOrNull(r['holder_id']),
    holder_name:    asStringOrNull(r['holder_name']),
    server_id:      asStringOrNull(r['server_id']),
    awarded_iso:    asString(r['awarded_iso']),
    transfer_count: asNumber(r['transfer_count']),
  }))
}

// ─── Global Stats ─────────────────────────────────────────────
export function adaptGlobalStats(raw: unknown): GlobalStatsUI {
  const r = asRecord(raw)
  return {
    total_kills:             asNumber(r['total_kills']),
    active_players:          asNumber(r['active_players']),
    trophies_in_circulation: asNumber(r['trophies_in_circulation']),
    active_servers:          asNumber(r['active_servers']),
  }
}

// ─── Alerts ───────────────────────────────────────────────────
export function adaptAlertRules(raw: unknown): AlertRuleUI[] {
  return asArray<Raw>(raw).map(r => ({
    id:             asString(r['id']),
    name:           asString(r['name']),
    condition:      asStringOrNull(r['condition']),
    channel:        asString(r['channel']),
    enabled:        asBool(r['enabled']),
    last_fired_iso: asStringOrNull(r['last_fired_iso']),
  }))
}

export function adaptAlertHistory(raw: unknown): AlertHistoryUI[] {
  return asArray<Raw>(raw).map(r => ({
    id:             asString(r['id']),
    rule_name:      asString(r['rule_name']),
    fired_iso:      asString(r['fired_iso']),
    detail:         asString(r['detail']),
    server_id:      asString(r['server_id']),
  }))
}
