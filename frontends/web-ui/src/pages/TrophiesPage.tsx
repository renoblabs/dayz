import { useTrophies } from '../hooks/useDashboardData'
import { PlayerAvatar } from '../components/icons'
import { fmtAgo } from '../lib/format'

function Chalice() {
  return (
    <svg viewBox="0 0 64 64" width={48} height={48} style={{ color: 'var(--amber)', filter: 'drop-shadow(0 0 8px var(--amber-soft))' }}>
      <path fill="currentColor" d="M16 8 h32 v12 c0 8 -4 14 -10 16 v6 h6 v8 h-24 v-8 h6 v-6 c-6 -2 -10 -8 -10 -16 z"/>
      <rect x="22" y="50" width="20" height="3" fill="currentColor" opacity="0.6"/>
    </svg>
  )
}

export default function TrophiesPage() {
  const { data: trophies = [], isLoading } = useTrophies()

  return (
    <main style={{ padding: 16 }}>
      <div className="panel tick-corners">
        <div className="panel-header">
          <div className="panel-title">
            <span className="corner" />TROPHIES IN CIRCULATION
          </div>
        </div>
        <div className="panel-body">
          {isLoading && trophies.length === 0 && (
            <div className="t-label" style={{ padding: 40, textAlign: 'center' }}>
              FETCHING REWARDS...
            </div>
          )}

          {!isLoading && trophies.length === 0 && (
            <div className="t-mono" style={{ padding: 40, textAlign: 'center', color: 'var(--fg-4)' }}>
              NO TROPHIES HAVE BEEN CLAIMED YET
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
            {trophies.map((t) => (
              <div
                key={t.id}
                className="panel"
                style={{
                  position: 'relative',
                  padding: 16,
                  background: 'linear-gradient(180deg, var(--amber-soft) 0%, transparent 70%), var(--bg-1)',
                  borderColor: 'var(--amber-line)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Chalice />
                  <div>
                    <div className="t-display" style={{ color: 'var(--amber)', fontSize: 12, letterSpacing: '0.14em' }}>
                      {t.trophy_class}
                    </div>
                    <div className="t-mono" style={{ color: 'var(--fg-3)', fontSize: 10.5, marginTop: 2 }}>
                      from {t.boss_type}
                    </div>
                  </div>
                </div>

                <div className="divider-h" />

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <PlayerAvatar name={t.holder_name ?? 'Unknown'} size={26} />
                  <div className="t-mono" style={{ color: 'var(--fg-2)', fontSize: 12 }}>{t.holder_name ?? 'Unknown'}</div>
                </div>

                <div className="t-mono" style={{ marginTop: 10, fontSize: 10, color: 'var(--fg-4)', letterSpacing: '0.14em' }}>
                  AWARDED {fmtAgo(t.awarded_iso).toUpperCase()} · {t.transfer_count} TRANSFER{t.transfer_count === 1 ? '' : 'S'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  )
}
