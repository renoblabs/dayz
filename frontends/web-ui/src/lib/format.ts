/* Small formatters for the dashboard. Pure, no deps beyond stdlib. */

export function fmtUptime(seconds: number | null | undefined): string {
  if (!seconds || !Number.isFinite(seconds)) return '—'
  const s = Math.floor(seconds)
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (d > 0) return `${d}d ${h}h ${m}m`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export function fmtAgo(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return '—'
  const t = Date.parse(iso)
  if (!Number.isFinite(t)) return '—'
  const diff = (now.getTime() - t) / 1000
  if (diff < 5) return 'just now'
  if (diff < 60) return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export function fmtTtk(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return '—'
  if (seconds < 60) return `${seconds.toFixed(0)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}m${s.toString().padStart(2, '0')}s`
}

export function fmtPercent(v: number | null | undefined, digits = 0): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return `${(v * 100).toFixed(digits)}%`
}

export function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v))
}

export function summarizeEvent(eventType: string, data: Record<string, unknown>): string {
  switch (eventType) {
    case 'boss.killed': {
      const boss = (data?.boss_display_name as string) ?? 'unknown boss'
      const killerObj = (data?.killer as Record<string, unknown> | undefined) ?? {}
      const killer = (killerObj?.player_name as string) ?? (data?.killer_player_name as string) ?? 'unknown'
      const ttk = data?.time_to_kill_seconds
      const ttkStr = typeof ttk === 'number' ? ` · ${fmtTtk(ttk)}` : ''
      return `${boss} killed by ${killer}${ttkStr}`
    }
    case 'boss.spawned': {
      const boss = (data?.boss_display_name as string) ?? 'unknown boss'
      return `${boss} spawned`
    }
    case 'player.connected': {
      const name = (data?.player_name as string) ?? 'someone'
      return `${name} joined`
    }
    case 'player.disconnected': {
      const name = (data?.player_name as string) ?? 'someone'
      const mins = data?.session_minutes
      return typeof mins === 'number' ? `${name} left after ${mins}m` : `${name} left`
    }
    case 'server.heartbeat': {
      const pc = data?.player_count as number | undefined
      const ab = data?.active_boss_count as number | undefined
      return `heartbeat · ${pc ?? '?'} players · ${ab ?? 0} active bosses`
    }
    case 'trophy.awarded': {
      const cls = (data?.trophy_class as string) ?? 'trophy'
      const holder = (data?.holder_name as string) ?? '?'
      return `${cls} → ${holder}`
    }
    default: {
      const cls = data?.custom_event_type
      return typeof cls === 'string' ? `custom: ${cls}` : eventType
    }
  }
}

export function eventCategory(eventType: string): 'boss' | 'player' | 'server' | 'trophy' | 'other' {
  if (eventType.startsWith('boss')) return 'boss'
  if (eventType.startsWith('player')) return 'player'
  if (eventType.startsWith('server')) return 'server'
  if (eventType.startsWith('trophy')) return 'trophy'
  return 'other'
}
