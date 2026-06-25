import { useRecentEncounters } from '../../hooks/useDashboardData'
import { PlayerAvatar, getBossIcon } from '../icons'
import { fmtAgo, fmtTtk } from '../../lib/format'

export function SidebarRecentEncounters() {
  const { data, isLoading } = useRecentEncounters(8)

  return (
    <div className="panel tick-corners">
      <div className="panel-header">
        <div className="panel-title">
          <span className="corner" />
          <span>Recent Encounters</span>
        </div>
      </div>
      <div className="panel-body" style={{ padding: '8px 0 14px' }}>
        {isLoading || !data ? (
          <div style={{ padding: 14 }} className="t-label">Loading…</div>
        ) : data.items.length === 0 ? (
          <div style={{ padding: 14 }} className="t-label">No encounters yet.</div>
        ) : (
          <div style={{ position: 'relative' }}>
            {/* vertical timeline rail */}
            <div style={{ position: 'absolute', left: 27, top: 6, bottom: 6, width: 1, background: 'var(--line-soft)' }} />
            {data.items.map((e) => {
              const BossIco = getBossIcon(e.boss_type)
              return (
                <div key={e.id} style={{ display: 'grid', gridTemplateColumns: '54px 1fr', alignItems: 'flex-start', padding: '6px 14px' }}>
                  <div style={{ position: 'relative', height: 24 }}>
                    {/* diamond node */}
                    <div style={{
                      position: 'absolute',
                      left: 22, top: 6,
                      width: 10, height: 10,
                      transform: 'rotate(45deg)',
                      border: '1px solid var(--amber-line)',
                      background: 'var(--amber-soft)',
                    }} />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ color: 'var(--amber)', display: 'inline-flex' }}>
                        <BossIco size={12} />
                      </span>
                      <span className="t-mono" style={{ color: 'var(--amber)', fontSize: 10.5, letterSpacing: '0.10em' }}>
                        {e.boss_type}
                      </span>
                      <span className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10, marginLeft: 'auto' }}>
                        {fmtAgo(e.killed_at ?? e.spawned_at)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {e.killer_player_name && <PlayerAvatar name={e.killer_player_name} size={16} />}
                      <span className="t-mono" style={{ color: 'var(--fg-2)', fontSize: 11 }}>
                        {e.killer_player_name ?? '—'}
                      </span>
                      <span style={{ color: 'var(--fg-4)' }}>·</span>
                      <span className="t-mono" style={{ color: 'var(--fg-3)', fontSize: 10.5 }}>
                        {fmtTtk(e.time_to_kill_seconds)}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
