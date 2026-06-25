/* ─────────────────────────────────────────────────────────────────
   Synthetic / illustrative mock data for tabs whose backend tables
   don't exist yet. The names and IDs below are fictional placeholders
   used only to demonstrate the UI; the Steam64 IDs follow an
   obviously-fake 7656119xxxxxxxxxx pattern and do not identify any
   real player. Replace with live data once the backend tables exist.
   ───────────────────────────────────────────────────────────────── */

export interface MockPlayer {
  steam_id: string
  name: string
  status: 'online' | 'offline'
  flagged: boolean
  boss_kills: number
  hours: number
  last_seen: string  // ISO or 'now'
  joined: string
  current_server_id: string | null
  recent_sessions: { server: string; mins: number; ago: string }[]
}

export const MOCK_PLAYERS: MockPlayer[] = [
  {
    steam_id: '76561190000000001',
    name: '[TPG] cleric_ozz',
    status: 'online',
    flagged: false,
    boss_kills: 37,
    hours: 412,
    last_seen: 'now',
    joined: '2026-01-14',
    current_server_id: 'server_01',
    recent_sessions: [
      { server: 'server_01', mins: 184, ago: '2h ago' },
      { server: 'server_01', mins: 92,  ago: '1d ago' },
      { server: 'server_02', mins: 47,  ago: '3d ago' },
    ],
  },
  {
    steam_id: '76561190000000002',
    name: 'gnarlybeard',
    status: 'online',
    flagged: false,
    boss_kills: 28,
    hours: 318,
    last_seen: 'now',
    joined: '2026-02-03',
    current_server_id: 'server_01',
    recent_sessions: [
      { server: 'server_01', mins: 220, ago: '4h ago' },
      { server: 'server_03', mins: 60,  ago: '2d ago' },
    ],
  },
  {
    steam_id: '76561190000000003',
    name: '[SVR] m1k3wash',
    status: 'offline',
    flagged: false,
    boss_kills: 22,
    hours: 287,
    last_seen: '2026-05-01T22:14:00Z',
    joined: '2025-11-22',
    current_server_id: null,
    recent_sessions: [
      { server: 'server_02', mins: 145, ago: '14h ago' },
    ],
  },
  {
    steam_id: '76561190000000004',
    name: 'crustyheist',
    status: 'offline',
    flagged: true,
    boss_kills: 19,
    hours: 244,
    last_seen: '2026-04-30T11:00:00Z',
    joined: '2025-12-08',
    current_server_id: null,
    recent_sessions: [
      { server: 'server_01', mins: 98, ago: '2d ago' },
    ],
  },
  {
    steam_id: '76561190000000005',
    name: '[WLF] vyperknight',
    status: 'online',
    flagged: false,
    boss_kills: 15,
    hours: 199,
    last_seen: 'now',
    joined: '2026-03-11',
    current_server_id: 'server_03',
    recent_sessions: [
      { server: 'server_03', mins: 175, ago: '6h ago' },
    ],
  },
  {
    steam_id: '76561190000000006',
    name: 'swedish_meatbro',
    status: 'offline',
    flagged: false,
    boss_kills: 12,
    hours: 178,
    last_seen: '2026-04-29T18:30:00Z',
    joined: '2026-01-30',
    current_server_id: null,
    recent_sessions: [
      { server: 'server_02', mins: 80, ago: '3d ago' },
    ],
  },
  {
    steam_id: '76561190000000007',
    name: '[419] sauceboss',
    status: 'online',
    flagged: false,
    boss_kills: 9,
    hours: 156,
    last_seen: 'now',
    joined: '2026-02-21',
    current_server_id: 'server_01',
    recent_sessions: [
      { server: 'server_01', mins: 60, ago: '5h ago' },
    ],
  },
  {
    steam_id: '76561190000000008',
    name: 'panko_breaded',
    status: 'offline',
    flagged: false,
    boss_kills: 7,
    hours: 134,
    last_seen: '2026-04-30T03:00:00Z',
    joined: '2025-10-04',
    current_server_id: null,
    recent_sessions: [
      { server: 'server_01', mins: 110, ago: '2d ago' },
    ],
  },
  {
    steam_id: '76561190000000009',
    name: '[INF] dramamine42',
    status: 'online',
    flagged: false,
    boss_kills: 5,
    hours: 102,
    last_seen: 'now',
    joined: '2026-03-19',
    current_server_id: 'server_02',
    recent_sessions: [
      { server: 'server_02', mins: 45, ago: '1h ago' },
    ],
  },
  {
    steam_id: '76561190000000010',
    name: 'tarp_papi',
    status: 'offline',
    flagged: false,
    boss_kills: 4,
    hours: 88,
    last_seen: '2026-04-28T22:00:00Z',
    joined: '2026-04-01',
    current_server_id: null,
    recent_sessions: [
      { server: 'server_03', mins: 35, ago: '4d ago' },
    ],
  },
]

// ─── SERVERS (cards 2 & 3 are mock; card 1 pulls real /server/status) ──
export interface MockServerCard {
  server_id: string
  name: string
  map: 'chernarusplus' | 'livonia' | 'namalsk'
  player_count: number
  player_max: number
  uptime_seconds: number
  active_boss_count: number
  bosssignal_version: string
  is_mock: true
}

export const MOCK_SERVER_CARDS: MockServerCard[] = [
  {
    server_id: 'server_02',
    name: 'tisy_hermit',
    map: 'livonia',
    player_count: 18,
    player_max: 60,
    uptime_seconds: 86400 * 4 + 3600 * 6,
    active_boss_count: 1,
    bosssignal_version: '0.1.0',
    is_mock: true,
  },
  {
    server_id: 'server_03',
    name: 'Coast_Bambi',
    map: 'namalsk',
    player_count: 7,
    player_max: 40,
    uptime_seconds: 86400 + 3600 * 11,
    active_boss_count: 0,
    bosssignal_version: '0.1.0',
    is_mock: true,
  },
]

// ─── TROPHIES (mock — backend table not yet wired) ─────────────────
// boss_type uses neutral ExampleBoss_* placeholders; substitute the
// classnames of your own boss/content mod (or a licensed third-party
// boss mod). ZmbM_MarksTester / ZmbF_BetaQueen are example MarksContent
// classes.
export interface MockTrophy {
  id: string
  trophy_class: string
  boss_type: string
  holder_name: string
  awarded_iso: string
  transfer_count: number
}

export const MOCK_TROPHIES: MockTrophy[] = [
  { id: 't1', trophy_class: 'TROPHY_BetaQueen_Skull',     boss_type: 'ZmbF_BetaQueen',         holder_name: '[TPG] cleric_ozz',       awarded_iso: '2026-04-30T18:14:00Z', transfer_count: 0 },
  { id: 't2', trophy_class: 'TROPHY_ExampleBoss04_Plate', boss_type: 'ExampleBoss_04',         holder_name: 'gnarlybeard',            awarded_iso: '2026-04-29T11:00:00Z', transfer_count: 2 },
  { id: 't3', trophy_class: 'TROPHY_ExampleBoss02_Crown', boss_type: 'ExampleBoss_02',         holder_name: '[SVR] m1k3wash',         awarded_iso: '2026-04-26T09:30:00Z', transfer_count: 1 },
  { id: 't4', trophy_class: 'TROPHY_ExampleBoss03_Badge', boss_type: 'ExampleBoss_03',         holder_name: '[WLF] vyperknight',      awarded_iso: '2026-04-22T14:55:00Z', transfer_count: 4 },
  { id: 't5', trophy_class: 'TROPHY_ExampleBoss01_Scope', boss_type: 'ExampleBoss_01',         holder_name: 'crustyheist',            awarded_iso: '2026-04-19T20:08:00Z', transfer_count: 0 },
  { id: 't6', trophy_class: 'TROPHY_MarksTester_Hat',     boss_type: 'ZmbM_MarksTester',       holder_name: 'swedish_meatbro',        awarded_iso: '2026-04-15T22:30:00Z', transfer_count: 1 },
]

// ─── ALERTS (mock — backend has no alerts table) ───────────────────
export interface MockAlertRule {
  id: string
  name: string
  condition: string
  channel: string
  last_fired_iso: string | null
  enabled: boolean
}

export const MOCK_ALERT_RULES: MockAlertRule[] = [
  { id: 'a1', name: 'Player count > 50',         condition: 'player_count > 50',                channel: 'discord:#ops',         last_fired_iso: '2026-04-30T22:14:00Z', enabled: true  },
  { id: 'a2', name: 'Boss spawned during night', condition: 'boss.spawned AND hour BETWEEN 0 5', channel: 'discord:#bosses',     last_fired_iso: '2026-04-29T03:18:00Z', enabled: true  },
  { id: 'a3', name: 'Server heartbeat lapse',    condition: 'last_heartbeat > 5min',            channel: 'pagerduty:oncall',     last_fired_iso: null,                    enabled: true  },
  { id: 'a4', name: 'Player flagged for raid',   condition: 'flagged_kill_count > 3',           channel: 'discord:#mods',        last_fired_iso: '2026-04-26T12:45:00Z', enabled: false },
  { id: 'a5', name: 'Trophy transferred 5x',     condition: 'trophy.transfer_count >= 5',       channel: 'discord:#trophies',    last_fired_iso: '2026-04-22T18:20:00Z', enabled: true  },
]

export interface MockAlertFire {
  id: string
  rule_name: string
  fired_iso: string
  detail: string
}

export const MOCK_ALERT_FIRES: MockAlertFire[] = [
  { id: 'f1', rule_name: 'Player count > 50',         fired_iso: '2026-04-30T22:14:00Z', detail: 'server_01 hit 54 players' },
  { id: 'f2', rule_name: 'Boss spawned during night', fired_iso: '2026-04-29T03:18:00Z', detail: 'ExampleBoss_02 on server_02' },
  { id: 'f3', rule_name: 'Player flagged for raid',   fired_iso: '2026-04-26T12:45:00Z', detail: 'crustyheist — 4 flagged kills in 30m' },
  { id: 'f4', rule_name: 'Trophy transferred 5x',     fired_iso: '2026-04-22T18:20:00Z', detail: 'TROPHY_ExampleBoss03_Badge — 5 transfers' },
]
