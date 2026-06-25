import { useAlertRules, useAlertHistory } from '../hooks/useDashboardData'
import { fmtAgo } from '../lib/format'

export default function AlertsPage() {
  const { data: rules = [], isLoading: loadingRules } = useAlertRules()
  const { data: history = [], isLoading: loadingHistory } = useAlertHistory()

  return (
    <main className="stack-on-mobile" style={{ padding: 16, display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 340px', gap: 16, alignItems: 'start' }}>
      {/* Rules */}
      <div className="panel tick-corners">
        <div className="panel-header">
          <div className="panel-title">
            <span className="corner" />ALERT RULES
          </div>
          <button className="btn-ghost" disabled title="// stub: backend write paths not wired">+ NEW RULE</button>
        </div>
        <div>
          {loadingRules && rules.length === 0 && (
            <div className="panel-body t-label">SYNCING RULES...</div>
          )}
          {rules.length === 0 && !loadingRules && (
            <div className="panel-body t-mono" style={{ color: 'var(--fg-4)' }}>NO RULES DEFINED</div>
          )}
          {rules.map((r) => (
            <div
              key={r.id}
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(0,1fr) 110px 60px 70px',
                gap: 14,
                alignItems: 'center',
                padding: '10px 14px',
                borderBottom: '1px solid var(--line-soft)',
                opacity: r.enabled ? 1 : 0.55,
              }}
            >
              <div>
                <div className="t-mono" style={{ color: 'var(--fg)', fontSize: 12 }}>{r.name}</div>
                <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10.5, marginTop: 2 }}>{r.condition || 'no filter'}</div>
              </div>
              <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10.5 }}>
                {r.last_fired_iso ? fmtAgo(r.last_fired_iso) : 'never'}
              </div>
              <div
                className="chip"
                style={{
                  background: r.enabled ? 'var(--amber-soft)' : 'transparent',
                  borderColor: r.enabled ? 'var(--amber-line)' : 'var(--line)',
                  color: r.enabled ? 'var(--amber)' : 'var(--fg-3)',
                  textAlign: 'center'
                }}
              >
                {r.enabled ? 'ON' : 'OFF'}
              </div>
              <button className="btn-ghost" disabled title="// stub: not wired">EDIT</button>
            </div>
          ))}
        </div>
      </div>

      {/* Recent fires */}
      <aside className="panel tick-corners">
        <div className="panel-header">
          <div className="panel-title"><span className="corner" />RECENT FIRES</div>
        </div>
        <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {loadingHistory && history.length === 0 && (
            <div className="t-label">CHECKING HISTORY...</div>
          )}
          {history.length === 0 && !loadingHistory && (
            <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 11 }}>CLEAN SLATE</div>
          )}
          {history.map((f) => (
            <div key={f.id} style={{ borderLeft: '2px solid var(--ok)', paddingLeft: 10 }}>
              <div className="t-mono" style={{ color: 'var(--fg)', fontSize: 11 }}>{f.rule_name}</div>
              <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10, marginTop: 2 }}>
                {fmtAgo(f.fired_iso)} · {f.detail}
              </div>
            </div>
          ))}
        </div>
      </aside>
    </main>
  )
}
