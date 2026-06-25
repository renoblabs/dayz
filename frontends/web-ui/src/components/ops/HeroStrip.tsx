import { useMemo } from 'react'
import { useGlobalStats, useRecentEncounters } from '../../hooks/useDashboardData'

export function HeroStrip() {
  const { data: global } = useGlobalStats()
  const { data: enc } = useRecentEncounters(50)

  const activeEncounters = useMemo(() => {
    if (!enc) return 0
    return enc.items.filter((e) => e.status !== 'killed').length
  }, [enc])

  const stats = [
    { v: global?.active_players ?? 0,                l: 'TOTAL PLAYERS' },
    { v: activeEncounters,                            l: 'ACTIVE ENCOUNTERS' },
    { v: global?.active_servers ?? 0,                 l: 'SERVERS ONLINE' },
    { v: global?.total_kills ?? 0,                    l: 'TOTAL KILLS' },
  ]

  return (
    <section className="hero-strip">
      <div className="hero-rack left" />
      <div className="hero-rack right" />
      <div className="hero-content">
        <div>
          <div className="hero-title">DAYZ NETWORK</div>
          <div className="hero-tag">Operator Panel · Live</div>
        </div>
        <div className="hero-meta">
          {stats.map((s) => (
            <div key={s.l} className="hero-stat">
              <div className="v">{s.v}</div>
              <div className="l">{s.l}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
