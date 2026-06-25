// BossSignal API types — mirrors bosssignal-backend schemas.

export interface ApiHealth {
  status: string;
  version: string;
}

export interface ActiveBoss {
  boss_id: string;
  boss_type: string;
  display_name: string;
  elapsed_seconds: number;
  health_pct: number;
}

// Raw API shape returned by GET /api/v1/server/status
export interface ServerStatus {
  server_id: string;
  last_seen: string | null;
  is_online: boolean;
  player_count: number;
  active_boss_count: number;
  active_bosses: ActiveBoss[];
  bosssignal_version: string | null;
  uptime_seconds?: number | null;
  is_mock?: boolean;
}

export interface Event {
  id: string;
  server_id: string;
  event_type: string;
  received_at: string;
  data: Record<string, unknown>;
}

// SSE broadcast shape (what the /events/stream endpoint yields)
export interface StreamedEvent {
  id: string;
  server_id: string;
  event_type: string;
  received_at: string;
  data: Record<string, unknown>;
}

// ──────────────────────────────────────────────────────────────────────────────
// HiveAPI types (separate product, port 8090, /v1/* routes)
// ──────────────────────────────────────────────────────────────────────────────

export interface HiveOverview {
  players: number;
  characters: number;
  servers: number;
  recent_events: number;
  timestamp: string;
}

export interface HiveEvent {
  id: string;
  type: string;
  timestamp: string;
  server_id?: string;
  actor?: string;
  object_id?: string;
  payload: Record<string, unknown>;
}

// ─────────────────────────────────────────────────────────────────────────────
// UI shapes — what panels consume after adapters.ts maps the raw API responses.
// Suffixed UI to distinguish from raw API types where the field names diverge.
// Source: _design-handoff-staging/.../README.md "Mock Data Shapes" section,
// reconciled against the actual API responses observed at :6700.
// ─────────────────────────────────────────────────────────────────────────────

export type DayZMap = 'chernarusplus' | 'livonia' | 'namalsk';

export interface LoadedMod {
  name: string;
  version: string;
  status: 'ok' | 'warn' | 'bad';
}

export interface ServerPerf {
  tick: number;
  fps: number;
  mem: number; // 0..1
}

export interface ServerStatusUI {
  server_id: string;          // raw API id (kept for keys/stable refs)
  name: string;               // display label — falls back to server_id
  map: DayZMap | null;        // null when backend can't tell us yet
  player_count: number;
  player_max: number | null;  // null until backend tracks it
  uptime_seconds: number | null;
  last_heartbeat: string | null; // ISO-8601 UTC
  bosssignal_version: string | null;
  loaded_mods: LoadedMod[] | null; // null = empty-state in UI
  perf: ServerPerf | null;         // null = empty-state in UI
  is_online: boolean;
  active_boss_count: number;
  active_bosses: ActiveBoss[];
  is_mock: boolean;
}

export interface EventUI {
  id: string;
  event_type: string;
  server_id: string;
  received_at: string;
  data: Record<string, unknown>;
  __fresh?: boolean;
}

export interface LeaderboardEntryUI {
  rank: number;
  player_id: string;
  player_name: string;
  boss_kills: number;
  fastest_kill_sec: number | null;
  favorite_boss?: string;
  favorite_weapon?: string;
  is_mock?: boolean;
}

export interface LeaderboardUI {
  window_days: number;
  rows: LeaderboardEntryUI[];
  is_mock: boolean;
}

export interface EncounterUI {
  id: string;
  server_id: string;
  boss_id: string;
  boss_type: string;
  display_name: string;
  spawned_at: string | null;
  killed_at: string | null;
  time_to_kill_seconds: number | null;
  killer_player_id: string | null;
  killer_player_name: string | null;
  killer_weapon: string | null;
  player_count_at_spawn: number | null;
  status: string;
  is_mock?: boolean;
}

export interface EncountersUI {
  items: EncounterUI[];
  is_mock: boolean;
}

export type KbSourceType =
  | 'bistudio_wiki'
  | 'yadz_docs'
  | 'github_mod_file'
  | 'youtube_transcript'
  | 'community_doc'
  | 'manual'
  | 'local_repo';

export interface KbSourceUI {
  id: string;
  url: string;
  source_type: KbSourceType | string;
  title: string | null;
  rel_path: string | null;
  sub_kind: string | null;
  text_len: number | null;
  fetched_at: string | null;
}

export interface KbSourcesPageUI {
  kb_available: boolean;
  page: number;
  page_size: number;
  total: number;
  items: KbSourceUI[];
}

export interface KbSearchHitUI {
  chunk_id: string;
  source_id: string;
  chunk_index: number;
  snippet: string;
  source_url: string;
  source_type: string;
  title: string | null;
  score: number; // 0..1 (BM25 ts_rank_cd is unbounded; we clamp on display)
}

export interface KbSearchUI {
  kb_available: boolean;
  query: string;
  limit: number;
  items: KbSearchHitUI[];
}

export interface KbChunkUI {
  id: string;
  chunk_index: number;
  text: string;
  metadata: Record<string, unknown>;
  has_embedding: boolean;
}

export interface KbSourceDetailUI {
  kb_available: boolean;
  source: (KbSourceUI & {
    content_hash: string;
    raw_len: number;
    cleaned_len: number;
    metadata: Record<string, unknown>;
  }) | null;
  chunks: KbChunkUI[];
  chunk_count: number;
}

export interface SystemHealthSubsystemUI {
  status: string; // 'ok' | 'unconfigured' | 'unreachable' | 'error' | 'fresh' | 'stale' | ...
  detail?: string | null;
}

export interface SystemHealthUI {
  bosssignal_db: SystemHealthSubsystemUI;
  kb_db: SystemHealthSubsystemUI;
  kb_corpus: {
    sources?: number;
    chunks?: number;
    embedded?: number;
    embed_percent?: number;
  };
  snapshotter: {
    status: string;
    last_capture?: string | null;
    age_hours?: number | null;
    days_banked?: number | null;
    total_rows?: number | null;
    detail?: string | null;
  };
  checked_at: string;
}

export interface PlayerUI {
  steam_id: string;
  name: string;
  status: 'online' | 'offline' | string;
  boss_kills: number;
  hours: number;
  last_seen: string;
  joined_at: string;
  flagged: boolean;
  current_server_id: string | null;
}

export interface TrophyUI {
  id: string;
  trophy_class: string;
  boss_type: string;
  holder_id: string | null;
  holder_name: string | null;
  server_id: string | null;
  awarded_iso: string;
  transfer_count: number;
}

export interface GlobalStatsUI {
  total_kills: number;
  active_players: number;
  trophies_in_circulation: number;
  active_servers: number;
}

export interface AlertRuleUI {
  id: string;
  name: string;
  condition: string | null;
  channel: string;
  enabled: boolean;
  last_fired_iso: string | null;
}

export interface AlertHistoryUI {
  id: string;
  rule_name: string;
  fired_iso: string;
  detail: string;
  server_id: string;
}
