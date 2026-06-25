import { useSharedEventStream } from '../../hooks/eventStreamContext'
import { useSystemHealth } from '../../hooks/useDashboardData'

type Severity = 'ok' | 'warn' | 'bad' | 'idle'

function dotFor(status: string): Severity {
  if (['ok', 'fresh', 'healthy'].includes(status)) return 'ok'
  if (['warn', 'stale', 'unconfigured'].includes(status)) return 'warn'
  if (['bad', 'error', 'unreachable'].includes(status)) return 'bad'
  return 'idle'
}

export function HealthStrip() {
  const { data: h } = useSystemHealth()
  const { isConnected } = useSharedEventStream()

  const items: { label: string; value: string; sev: Severity; tip: string }[] = [
    {
      label: 'POSTGRES',
      value: h?.bosssignal_db.status ?? '—',
      sev: dotFor(h?.bosssignal_db.status ?? 'unknown'),
      tip: h?.bosssignal_db.detail ?? 'BossSignal events DB',
    },
    {
      label: 'API',
      value: h ? 'ok' : '—',
      sev: h ? 'ok' : 'idle',
      tip: 'BossSignal HTTP API self-ping',
    },
    {
      label: 'KB',
      value: h?.kb_db.status ?? '—',
      sev: dotFor(h?.kb_db.status ?? 'unknown'),
      tip: h ? `${h.kb_corpus.sources ?? 0} sources / ${h.kb_corpus.chunks ?? 0} chunks / ${h.kb_corpus.embed_percent ?? 0}% embedded` : 'Knowledge base postgres',
    },
    {
      label: 'SNAPSHOT',
      value: h?.snapshotter.status ?? '—',
      sev: dotFor(h?.snapshotter.status ?? 'unknown'),
      tip: h?.snapshotter.last_capture ? `last: ${new Date(h.snapshotter.last_capture).toUTCString()} (${h.snapshotter.age_hours?.toFixed?.(1) ?? '?'}h ago, ${h.snapshotter.days_banked ?? 0} days banked)` : 'Battlemetrics + Workshop nightly',
    },
    {
      label: 'SSE',
      value: isConnected ? 'connected' : 'offline',
      sev: isConnected ? 'ok' : 'bad',
      tip: '/api/v1/events/stream',
    },
  ]

  return (
    <div className="healthstrip">
      {items.map((it) => (
        <div key={it.label} className="item" title={it.tip}>
          <span className={`dot ${it.sev}`} />
          <span className="label">{it.label}</span>
          <span className="value">{it.value}</span>
        </div>
      ))}
      <div style={{ marginLeft: 'auto', color: 'var(--fg-4)' }}>
        {h ? `as of ${new Date(h.checked_at).toLocaleTimeString()}` : '—'}
      </div>
    </div>
  )
}
