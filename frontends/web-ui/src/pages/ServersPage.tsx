import { useServers } from '../hooks/useDashboardData'
import { fmtUptime, fmtAgo } from '../lib/format'
import { MOCK_SERVER_CARDS } from '../lib/mockData'
import { MapSilhouette } from '../components/icons'
import type { DayZMap } from '../types'

interface CardData {
  server_id: string
  name: string
  map: DayZMap
  player_count: number
  player_max: number | null
  uptime_seconds: number | null
  active_boss_count: number
  version: string | null
  last_heartbeat: string | null
  is_online: boolean
  is_mock: boolean
}

function ServerCard({ d }: { d: CardData }) {
  const Map = MapSilhouette[d.map] ?? MapSilhouette.chernarusplus
  const popPct = d.player_max ? Math.min(1, d.player_count / d.player_max) : 0
  return (
    <div className="panel tick-corners" style={{ position: 'relative', overflow: 'hidden' }}>
      <div className="server-card-bg"><Map /></div>
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div className="panel-header">
          <div className="panel-title">
            <span className="corner" />
            {d.server_id}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className={`dot ${d.is_online ? 'ok live' : 'idle'}`} />
            <span className="t-mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
              {d.is_online ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>
        <div className="panel-body">
          <div className="t-display" style={{ color: 'var(--fg)', fontSize: 18 }}>{d.name}</div>
          <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10.5, letterSpacing: '0.14em', marginTop: 2 }}>
            MAP · {d.map.toUpperCase()}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 14 }}>
            <div>
              <div className="t-label">PLAYERS</div>
              <div className="t-num" style={{ color: 'var(--fg)', fontSize: 16 }}>
                {d.player_count}{d.player_max ? `/${d.player_max}` : ''}
              </div>
            </div>
            <div>
              <div className="t-label">UPTIME</div>
              <div className="t-num" style={{ color: 'var(--fg)', fontSize: 14 }}>{fmtUptime(d.uptime_seconds)}</div>
            </div>
            <div>
              <div className="t-label">ACTIVE BOSSES</div>
              <div className="t-num" style={{ color: 'var(--fg)', fontSize: 16 }}>{d.active_boss_count}</div>
            </div>
            <div>
              <div className="t-label">VERSION</div>
              <div className="t-mono" style={{ color: 'var(--fg-3)', fontSize: 11 }}>v{d.version ?? '—'}</div>
            </div>
          </div>

          <div className="bar-track" style={{ marginTop: 14 }}>
            <div className="bar-fill" style={{ width: `${(popPct * 100).toFixed(0)}%` }} />
          </div>
          <div className="t-mono" style={{ marginTop: 10, fontSize: 10, color: 'var(--fg-4)' }}>
            LAST HB · {fmtAgo(d.last_heartbeat)}
          </div>

          <div style={{ display: 'flex', gap: 6, marginTop: 14 }}>
            <button className="btn-ghost" disabled title="// stub: not wired">FOCUS</button>
            <button className="btn-ghost" disabled title="// stub: not wired">RESTART</button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ServersPage() {
  const { data: realServers, isLoading } = useServers()

  if (isLoading) {
    return (
      <main style={{ padding: 16 }}>
        <div className="t-label">Syncing server cluster…</div>
      </main>
    )
  }

  const cards: CardData[] = []
  
  if (realServers && realServers.length > 0) {
    for (const s of realServers) {
      cards.push({
        server_id: s.server_id,
        name: s.name,
        map: (s.map ?? 'chernarusplus') as DayZMap,
        player_count: s.player_count,
        player_max: s.player_max,
        uptime_seconds: s.uptime_seconds,
        active_boss_count: s.active_boss_count,
        version: s.bosssignal_version,
        last_heartbeat: s.last_heartbeat,
        is_online: s.is_online,
        is_mock: s.is_mock,
      })
    }
  } else {
    // Only show mock data if no real servers have ever connected
    for (const m of MOCK_SERVER_CARDS) {
      cards.push({
        server_id: m.server_id,
        name: m.name,
        map: m.map,
        player_count: m.player_count,
        player_max: m.player_max,
        uptime_seconds: m.uptime_seconds,
        active_boss_count: m.active_boss_count,
        version: m.bosssignal_version,
        last_heartbeat: new Date(Date.now() - 60_000).toISOString(),
        is_online: true,
        is_mock: true,
      })
    }
  }

  return (
    <main style={{ padding: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 16 }}>
        {cards.map((c) => <ServerCard key={c.server_id} d={c} />)}
      </div>
    </main>
  )
}
