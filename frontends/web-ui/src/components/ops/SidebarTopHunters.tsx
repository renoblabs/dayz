import { useLeaderboard } from '../../hooks/useDashboardData'
import { PlayerAvatar } from '../icons'

export function SidebarTopHunters() {
  const { data, isLoading } = useLeaderboard(7, 8)

  return (
    <div className="panel tick-corners">
      <div className="panel-header">
        <div className="panel-title">
          <span className="corner" />
          <span>Top Hunters · 7d</span>
        </div>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        {isLoading || !data ? (
          <div style={{ padding: 14 }} className="t-label">Loading…</div>
        ) : data.rows.length === 0 ? (
          <div style={{ padding: 14 }} className="t-label">No real boss kills yet.</div>
        ) : (
          data.rows.map((r, i) => {
            const podiumTint =
              i === 0 ? 'oklch(0.62 0.19 28 / 0.10)'
                : i === 1 ? 'oklch(0.62 0.19 28 / 0.06)'
                : i === 2 ? 'oklch(0.62 0.19 28 / 0.03)'
                : 'transparent'
            return (
              <div
                key={r.player_id || `mock-${r.rank}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '32px 28px 1fr auto',
                  gap: 10,
                  alignItems: 'center',
                  padding: '8px 14px',
                  borderBottom: '1px solid var(--line-soft)',
                  background: podiumTint,
                }}
              >
                <span className="t-num" style={{ color: i < 3 ? 'var(--amber)' : 'var(--fg-3)', fontSize: 14 }}>
                  #{r.rank}
                </span>
                <PlayerAvatar name={r.player_name} size={24} />
                <span className="t-mono" style={{ color: 'var(--fg)', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.player_name}
                </span>
                <span className="t-num" style={{ color: 'var(--fg)', fontSize: 13 }}>
                  {r.boss_kills}
                </span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
