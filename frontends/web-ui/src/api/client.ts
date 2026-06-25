/**
 * BossSignal backend axios client.
 * Base URL: VITE_API_BASE (e.g. http://127.0.0.1:6700) or relative paths
 * for same-origin deployment.
 *
 * Routes documented in:
 *   backends/bosssignal-backend/app/routers/{events,bosses,trophies,dashboard,kb}.py
 *   planning/dashboard-api-handoff-2026-05-01.md
 */
import axios from 'axios'
import type {
  ApiHealth,
  ServerStatus,
  Event,
  StreamedEvent,
  HiveOverview,
  HiveEvent,
} from '../types'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// HiveAPI is a separate product on port 8090/6701 with /v1/* routes (no /api prefix)
const hive = axios.create({
  baseURL: `${API_BASE}/v1`,
  headers: { 'Content-Type': 'application/json' },
})

export const apiClient = {
  async getHealth(): Promise<ApiHealth> {
    const { data } = await axios.get(`${API_BASE}/health`)
    return data
  },

  async getServers(): Promise<ServerStatus[]> {
    const { data } = await api.get('/servers')
    return data
  },

  async getEvents(params?: {
    limit?: number
    event_type?: string
    server_id?: string
  }): Promise<Event[]> {
    const { data } = await api.get('/events', { params })
    return data
  },

  // ── Dashboard read routes (added 2026-05-01) ─────────────────────
  async getServerStatus(serverId?: string): Promise<unknown> {
    const { data } = await api.get('/server/status', {
      params: serverId ? { server_id: serverId } : {},
    })
    return data
  },

  async getLeaderboardBossKills(days: number = 7, limit: number = 10): Promise<unknown> {
    const { data } = await api.get('/leaderboard/boss-kills', { params: { days, limit } })
    return data
  },

  async getEncountersRecent(limit: number = 20): Promise<unknown> {
    const { data } = await api.get('/encounters/recent', { params: { limit } })
    return data
  },

  async getSystemHealth(): Promise<unknown> {
    const { data } = await api.get('/system/health')
    return data
  },

  async getPlayers(limit: number = 200): Promise<unknown> {
    const { data } = await api.get('/players', { params: { limit } })
    return data
  },

  async getTrophies(): Promise<unknown> {
    const { data } = await api.get('/trophies')
    return data
  },

  async getGlobalStats(): Promise<unknown> {
    const { data } = await api.get('/stats')
    return data
  },

  async getAlertRules(): Promise<unknown> {
    const { data } = await api.get('/alerts/rules')
    return data
  },

  async getAlertHistory(): Promise<unknown> {
    const { data } = await api.get('/alerts/history')
    return data
  },

  // ── KB routes ────────────────────────────────────────────────────
  async getKbSources(opts: { type?: string; page?: number; page_size?: number } = {}): Promise<unknown> {
    const { data } = await api.get('/kb/sources', { params: opts })
    return data
  },

  async searchKb(q: string, limit: number = 15): Promise<unknown> {
    const { data } = await api.get('/kb/search', { params: { q, limit } })
    return data
  },

  async getKbSource(id: string): Promise<unknown> {
    const { data } = await api.get(`/kb/source/${encodeURIComponent(id)}`)
    return data
  },

  // ── Legacy SSE helper (kept for back-compat with old hooks; new code uses useEventStream) ──
  createEventStream(
    onEvent: (event: StreamedEvent) => void,
    onError?: (error: unknown) => void,
    onOpen?: () => void,
    serverId?: string,
  ): EventSource {
    const path = serverId
      ? `/api/v1/events/stream?server_id=${encodeURIComponent(serverId)}`
      : '/api/v1/events/stream'
    const url = API_BASE ? `${API_BASE}${path}` : path
    const es = new EventSource(url)
    es.onopen = () => onOpen?.()
    es.onmessage = (e) => {
      try {
        onEvent(JSON.parse(e.data))
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('SSE parse error:', err)
        onError?.(err)
      }
    }
    es.onerror = (err) => {
      // eslint-disable-next-line no-console
      console.error('SSE error:', err)
      onError?.(err)
    }
    return es
  },
}

export const hiveClient = {
  async getOverview(): Promise<HiveOverview> {
    const { data } = await hive.get('/admin/overview')
    return data
  },

  async getEvents(params?: { limit?: number; event_type?: string; server_id?: string }): Promise<HiveEvent[]> {
    const { data } = await hive.get('/admin/events', { params })
    return data
  },
}

export default apiClient
