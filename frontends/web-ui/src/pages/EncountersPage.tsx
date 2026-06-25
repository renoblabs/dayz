import { useMemo } from 'react'
import { useRecentEncounters } from '../hooks/useDashboardData'
import { fmtAgo, fmtTtk } from '../lib/format'
import { PlayerAvatar, getBossIcon } from '../components/icons'

const TTK_BUCKETS: { lo: number; hi: number; label: string }[] = [
  { lo: 0,   hi: 50,  label: '0–50s' },
  { lo: 50,  hi: 100, label: '50–100s' },
  { lo: 100, hi: 150, label: '100–150s' },
  { lo: 150, hi: 200, label: '150–200s' },
  { lo: 200, hi: 250, label: '200–250s' },
  { lo: 250, hi: Infinity, label: '250s+' },
]

export default function EncountersPage() {
  const { data, isLoading } = useRecentEncounters(200)

  const ttkData = useMemo(() => {
    if (!data) return []
    return TTK_BUCKETS.map((b) => {
      const count = data.items.filter((e) => {
        const t = e.time_to_kill_seconds
        return typeof t === 'number' && t >= b.lo && t < b.hi
      }).length
      return { ...b, count }
    })
  }, [data])

  const breakdown = useMemo(() => {
    if (!data) return []
    const counts = new Map<string, number>()
    for (const e of data.items) counts.set(e.boss_type, (counts.get(e.boss_type) ?? 0) + 1)
    const total = data.items.length
    return Array.from(counts.entries())
      .map(([cls, n]) => ({ cls, n, pct: total > 0 ? n / total : 0 }))
      .sort((a, b) => b.n - a.n)
      .slice(0, 8)
  }, [data])

  const maxBucket = Math.max(1, ...ttkData.map((b) => b.count))

  return (
    <main className="stack-on-mobile" style={{ padding: 16, display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 320px', gap: 16, alignItems: 'start' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* TTK histogram */}
        <div className="panel tick-corners">
          <div className="panel-header">
            <div className="panel-title">
              <span className="corner" />TTK DISTRIBUTION
            </div>
          </div>
          <div className="panel-body" style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 14, alignItems: 'end', minHeight: 160 }}>
            {ttkData.map((b) => {
              const h = (b.count / maxBucket) * 130
              return (
                <div key={b.label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                  <div className="t-num" style={{ color: 'var(--fg-2)', fontSize: 13 }}>{b.count}</div>
                  <div style={{ width: '70%', height: Math.max(2, h), background: 'var(--amber)', boxShadow: '0 0 8px var(--amber-soft)' }} />
                  <div className="t-mono" style={{ fontSize: 9.5, color: 'var(--fg-4)', letterSpacing: '0.10em' }}>{b.label}</div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Encounter table */}
        <div className="panel tick-corners">
          <div className="panel-header">
            <div className="panel-title"><span className="corner" />ALL ENCOUNTERS</div>
          </div>
          <div style={{ overflow: 'auto', maxHeight: 600 }}>
            {isLoading || !data ? (
              <div className="t-label" style={{ padding: 18 }}>Loading…</div>
            ) : data.items.length === 0 ? (
              <div className="t-label" style={{ padding: 18 }}>No real encounters recorded yet.</div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr>
                    {['BOSS', 'KILLER', 'SERVER', 'TTK', 'WHEN'].map((h, i) => (
                      <th key={i} style={{ textAlign: 'left', padding: '8px 14px', fontFamily: 'var(--f-mono)', fontSize: 10, letterSpacing: '0.18em', color: 'var(--fg-4)', borderBottom: '1px solid var(--line)' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((e) => {
                    const Boss = getBossIcon(e.boss_type)
                    return (
                      <tr key={e.id} style={{ borderBottom: '1px solid var(--line-soft)' }}>
                        <td style={{ padding: '6px 14px' }}>
                          <span style={{ color: 'var(--amber)', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                            <Boss size={12} />
                            <span className="t-mono" style={{ fontSize: 11 }}>{e.boss_type}</span>
                          </span>
                        </td>
                        <td style={{ padding: '6px 14px' }}>
                          {e.killer_player_name ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                              <PlayerAvatar name={e.killer_player_name} size={18} />
                              <span className="t-mono" style={{ color: 'var(--fg-2)', fontSize: 11 }}>{e.killer_player_name}</span>
                            </span>
                          ) : '—'}
                        </td>
                        <td style={{ padding: '6px 14px', color: 'var(--fg-3)' }} className="t-mono">{e.server_id}</td>
                        <td style={{ padding: '6px 14px', color: 'var(--fg-2)' }} className="t-num">{fmtTtk(e.time_to_kill_seconds)}</td>
                        <td style={{ padding: '6px 14px', color: 'var(--fg-4)' }} className="t-mono">{fmtAgo(e.killed_at ?? e.spawned_at)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Right sidebar — boss class breakdown */}
      <aside className="panel tick-corners">
        <div className="panel-header">
          <div className="panel-title"><span className="corner" />BOSS CLASSES</div>
        </div>
        <div className="panel-body">
          {breakdown.length === 0 ? (
            <div className="t-label">No data yet.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {breakdown.map(({ cls, n, pct }) => {
                const Ico = getBossIcon(cls)
                return (
                  <div key={cls}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ color: 'var(--amber)' }}><Ico size={12} /></span>
                      <span className="t-mono" style={{ color: 'var(--fg-2)', fontSize: 11, flex: 1 }}>{cls}</span>
                      <span className="t-num" style={{ color: 'var(--fg)', fontSize: 12 }}>{n}</span>
                    </div>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${(pct * 100).toFixed(0)}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </aside>
    </main>
  )
}
