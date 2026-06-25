import { useEffect, useState } from 'react'
import { useServerStatus } from '../../hooks/useDashboardData'
import { fmtAgo, fmtUptime, clamp } from '../../lib/format'
import { MapSilhouette } from '../icons'
import type { ServerStatusUI } from '../../types'

function useNowSec() {
  const [n, setN] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setN(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  return n
}

function CellBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: '12px 14px', borderRight: '1px solid var(--line-soft)' }}>
      <div className="t-label">{label}</div>
      <div style={{ marginTop: 4 }}>{children}</div>
    </div>
  )
}

interface ServerStatusPanelProps {
  server?: ServerStatusUI
  isLoading?: boolean
}

export function ServerStatusPanel({ server, isLoading: isLoadingProp }: ServerStatusPanelProps) {
  const { data: hookedServer, isLoading: isHookLoading } = useServerStatus()
  const now = useNowSec()

  const s = server || hookedServer
  const isLoading = server ? (isLoadingProp ?? false) : isHookLoading

  if (isLoading || !s) {
    return (
      <div className="panel tick-corners">
        <div className="panel-header">
          <div className="panel-title"><span className="corner" />Server · Live</div>
        </div>
        <div className="panel-body">
          <div className="t-label">Loading…</div>
        </div>
      </div>
    )
  }

  const heartbeatAgeS = s.last_heartbeat
    ? Math.max(0, Math.floor((now - Date.parse(s.last_heartbeat)) / 1000))
    : null
  const heartbeatStatus =
    heartbeatAgeS == null ? 'idle'
      : heartbeatAgeS < 120 ? 'ok'
      : heartbeatAgeS < 300 ? 'warn'
      : 'bad'

  const Map = s.map ? (MapSilhouette[s.map] ?? MapSilhouette.chernarusplus) : MapSilhouette.chernarusplus

  const popPct = s.player_max ? clamp(s.player_count / s.player_max, 0, 1) : 0

  return (
    <div className="panel tick-corners live-region" style={{ position: 'relative', overflow: 'hidden' }}>
      <div className="server-card-bg"><Map /></div>
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div className="panel-header">
          <div className="panel-title">
            <span className="corner" />
            <span>Server · Live</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="t-mono" style={{ fontSize: 10.5, color: 'var(--fg-3)', letterSpacing: '0.14em' }}>
              HEARTBEAT
            </span>
            <span className={`dot ${heartbeatStatus} ${heartbeatStatus === 'ok' ? 'live' : ''}`} />
            <span className="t-mono" style={{ fontSize: 11, color: 'var(--fg-2)' }}>
              {heartbeatAgeS == null ? '—' : `${heartbeatAgeS}s`}
            </span>
          </div>
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          {/* Top row */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', borderBottom: '1px solid var(--line-soft)' }}>
            <CellBlock label="Designation">
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span style={{ fontFamily: 'var(--f-display)', fontSize: 22, fontWeight: 600, letterSpacing: '0.06em', color: 'var(--fg)' }}>
                  {s.name}
                </span>
              </div>
              <div className="t-mono" style={{ fontSize: 10.5, color: 'var(--fg-4)', marginTop: 2, letterSpacing: '0.14em' }}>
                MAP · {(s.map ?? '—').toUpperCase()}
              </div>
            </CellBlock>
            <CellBlock label="Uptime">
              <div className="t-num" style={{ color: 'var(--fg)', fontSize: 16 }}>
                {fmtUptime(s.uptime_seconds)}
              </div>
              <div className="t-mono" style={{ fontSize: 10, color: 'var(--fg-4)', marginTop: 2, letterSpacing: '0.14em' }}>
                LAST HB · {fmtAgo(s.last_heartbeat, new Date(now))}
              </div>
            </CellBlock>
            <CellBlock label="Status">
              <div className="t-display" style={{ color: s.is_online ? 'var(--ok)' : 'var(--idle)', fontSize: 16 }}>
                {s.is_online ? 'ONLINE' : 'OFFLINE'}
              </div>
              <div className="t-mono" style={{ fontSize: 10, color: 'var(--fg-4)', marginTop: 2, letterSpacing: '0.14em' }}>
                v{s.bosssignal_version ?? '—'}
              </div>
            </CellBlock>
          </div>

          {/* Population */}
          <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--line-soft)' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
              <div className="t-label">Population</div>
              <div className="t-mono" style={{ fontSize: 11, color: 'var(--fg-2)' }}>
                {s.player_count}{s.player_max ? ` / ${s.player_max}` : ''}
              </div>
            </div>
            <div className="bar-track" style={{ marginTop: 6 }}>
              <div className="bar-fill" style={{ width: `${(popPct * 100).toFixed(0)}%` }} />
            </div>
          </div>

          {/* Perf cells */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: '1px solid var(--line-soft)' }}>
            <CellBlock label="Tick">
              <div className="t-num" style={{ color: 'var(--fg)', fontSize: 16 }}>
                {s.perf?.tick != null ? `${s.perf.tick.toFixed(1)} ms` : '[no data]'}
              </div>
            </CellBlock>
            <CellBlock label="FPS">
              <div className="t-num" style={{ color: 'var(--fg)', fontSize: 16 }}>
                {s.perf?.fps != null ? s.perf.fps.toFixed(0) : '[no data]'}
              </div>
            </CellBlock>
            <CellBlock label="Memory">
              <div className="t-num" style={{ color: 'var(--fg)', fontSize: 16 }}>
                {s.perf?.mem != null ? `${(s.perf.mem * 100).toFixed(0)}%` : '[no data]'}
              </div>
            </CellBlock>
          </div>

          {/* Loaded mods */}
          <div style={{ padding: '12px 14px' }}>
            <div className="t-label" style={{ marginBottom: 8 }}>Loaded Mods</div>
            {!s.loaded_mods || s.loaded_mods.length === 0 ? (
              <div className="t-mono" style={{ fontSize: 11, color: 'var(--fg-4)', letterSpacing: '0.12em' }}>
                [no data — backend doesn't expose mod manifest yet]
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 6 }}>
                {s.loaded_mods.map((m) => (
                  <div key={m.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px', border: '1px solid var(--line-soft)', background: 'var(--bg-inset)' }}>
                    <span className={`dot ${m.status}`} />
                    <span className="t-mono" style={{ fontSize: 11, color: 'var(--fg-2)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {m.name}
                    </span>
                    <span className="t-mono" style={{ fontSize: 9.5, color: 'var(--fg-4)' }}>{m.version}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
