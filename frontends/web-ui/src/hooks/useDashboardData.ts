/* ─────────────────────────────────────────────────────────────────
   useDashboardData — React Query hooks for every backend route the
   dashboard panels consume. Each runs the API call through the
   adapter so panels receive UI shapes, not raw API blobs.
   ───────────────────────────────────────────────────────────────── */

import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import {
  adaptServerStatus,
  adaptLeaderboard,
  adaptEncounters,
  adaptKbSources,
  adaptKbSearch,
  adaptKbSourceDetail,
  adaptSystemHealth,
  adaptPlayers,
  adaptTrophies,
  adaptGlobalStats,
  adaptAlertRules,
  adaptAlertHistory,
} from '../api/adapters'
import type {
  ServerStatusUI,
  LeaderboardUI,
  EncountersUI,
  KbSourcesPageUI,
  KbSearchUI,
  KbSourceDetailUI,
  SystemHealthUI,
  PlayerUI,
  TrophyUI,
  GlobalStatsUI,
  AlertRuleUI,
  AlertHistoryUI,
} from '../types'

const SHORT_STALE = 15_000   // server status, system health
const MID_STALE   = 60_000   // leaderboard, encounters list
const LONG_STALE  = 5 * 60_000 // KB browse pages

export function useServerStatus(serverId?: string): UseQueryResult<ServerStatusUI> {
  return useQuery({
    queryKey: ['server', 'status', serverId ?? 'default'],
    queryFn: async () => adaptServerStatus(await apiClient.getServerStatus(serverId) as Record<string, unknown>),
    staleTime: SHORT_STALE,
    refetchInterval: SHORT_STALE,
  })
}

export function useServers(): UseQueryResult<ServerStatusUI[]> {
  return useQuery({
    queryKey: ['servers', 'list'],
    queryFn: async () => {
      const raw = await apiClient.getServers() as unknown as Record<string, unknown>[]
      return raw.map(s => adaptServerStatus(s))
    },
    staleTime: SHORT_STALE,
    refetchInterval: SHORT_STALE,
  })
}

export function useLeaderboard(days: number = 7, limit: number = 10): UseQueryResult<LeaderboardUI> {
  return useQuery({
    queryKey: ['leaderboard', 'boss-kills', days, limit],
    queryFn: async () => adaptLeaderboard(await apiClient.getLeaderboardBossKills(days, limit) as Record<string, unknown>),
    staleTime: MID_STALE,
  })
}

export function useRecentEncounters(limit: number = 20): UseQueryResult<EncountersUI> {
  return useQuery({
    queryKey: ['encounters', 'recent', limit],
    queryFn: async () => adaptEncounters(await apiClient.getEncountersRecent(limit) as Record<string, unknown>),
    staleTime: MID_STALE,
  })
}

export function useSystemHealth(): UseQueryResult<SystemHealthUI> {
  return useQuery({
    queryKey: ['system', 'health'],
    queryFn: async () => adaptSystemHealth(await apiClient.getSystemHealth() as Record<string, unknown>),
    staleTime: SHORT_STALE,
    refetchInterval: SHORT_STALE,
  })
}

export interface UseKbSourcesOpts {
  type?: string
  page?: number
  page_size?: number
}
export function useKbSources(opts: UseKbSourcesOpts = {}): UseQueryResult<KbSourcesPageUI> {
  const page = opts.page ?? 1
  const pageSize = opts.page_size ?? 50
  return useQuery({
    queryKey: ['kb', 'sources', opts.type ?? 'all', page, pageSize],
    queryFn: async () => adaptKbSources(await apiClient.getKbSources({
      type: opts.type,
      page,
      page_size: pageSize,
    }) as Record<string, unknown>),
    staleTime: LONG_STALE,
  })
}

export function useKbSearch(query: string, limit: number = 15): UseQueryResult<KbSearchUI> {
  const enabled = query.trim().length > 0
  return useQuery({
    queryKey: ['kb', 'search', query, limit],
    queryFn: async () => adaptKbSearch(await apiClient.searchKb(query, limit) as Record<string, unknown>),
    enabled,
    staleTime: MID_STALE,
  })
}

export function useKbSource(id: string | null): UseQueryResult<KbSourceDetailUI> {
  return useQuery({
    queryKey: ['kb', 'source', id ?? ''],
    queryFn: async () => adaptKbSourceDetail(await apiClient.getKbSource(id!) as Record<string, unknown>),
    enabled: !!id,
    staleTime: LONG_STALE,
  })
}

export function usePlayers(limit: number = 200): UseQueryResult<PlayerUI[]> {
  return useQuery({
    queryKey: ['players', 'list', limit],
    queryFn: async () => adaptPlayers(await apiClient.getPlayers(limit)),
    staleTime: MID_STALE,
  })
}

export function useTrophies(): UseQueryResult<TrophyUI[]> {
  return useQuery({
    queryKey: ['trophies', 'list'],
    queryFn: async () => adaptTrophies(await apiClient.getTrophies()),
    staleTime: MID_STALE,
  })
}

export function useGlobalStats(): UseQueryResult<GlobalStatsUI> {
  return useQuery({
    queryKey: ['global', 'stats'],
    queryFn: async () => adaptGlobalStats(await apiClient.getGlobalStats()),
    staleTime: SHORT_STALE,
    refetchInterval: SHORT_STALE,
  })
}

export function useAlertRules(): UseQueryResult<AlertRuleUI[]> {
  return useQuery({
    queryKey: ['alerts', 'rules'],
    queryFn: async () => adaptAlertRules(await apiClient.getAlertRules()),
    staleTime: MID_STALE,
  })
}

export function useAlertHistory(): UseQueryResult<AlertHistoryUI[]> {
  return useQuery({
    queryKey: ['alerts', 'history'],
    queryFn: async () => adaptAlertHistory(await apiClient.getAlertHistory()),
    staleTime: SHORT_STALE,
    refetchInterval: SHORT_STALE,
  })
}
