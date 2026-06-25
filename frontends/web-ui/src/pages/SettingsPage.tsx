import { useTweaks } from '../state/tweaks'
import { ACCENT_HUES } from '../state/tweaks'

// Illustrative read-only values. Wire to a real config endpoint to show
// live settings; the values below are example placeholders.
const ROWS: { label: string; value: string; hint: string }[] = [
  { label: 'BACKEND URL',       value: import.meta.env.VITE_API_BASE ?? 'same-origin', hint: '// from VITE_API_BASE; same-origin if unset' },
  { label: 'SSE ENDPOINT',      value: '/api/v1/events/stream',                         hint: '// served by the backend' },
  { label: 'POSTGRES',          value: 'internal (compose)',                            hint: '// internal; not exposed to host' },
  { label: 'SNAPSHOT INTERVAL', value: 'nightly (workshop · servers)',                  hint: '// example schedule; configure per deployment' },
  { label: 'EMBEDDING MODEL',   value: 'configurable (optional)',                       hint: '// chunks.embedding column; partially backfilled' },
]

export default function SettingsPage() {
  const { hue, setHue } = useTweaks()

  return (
    <main style={{ padding: 16, maxWidth: 880, margin: '0 auto' }}>
      <div className="panel tick-corners">
        <div className="panel-header">
          <div className="panel-title"><span className="corner" />SETTINGS</div>
        </div>
        <div className="panel-body">
          {ROWS.map((r) => (
            <div key={r.label} style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 14, padding: '10px 0', borderBottom: '1px solid var(--line-soft)' }}>
              <div className="t-label">{r.label}</div>
              <div>
                <div className="t-mono" style={{ background: 'var(--bg-inset)', border: '1px solid var(--line)', padding: '6px 10px', color: 'var(--fg-2)', fontSize: 12 }}>
                  {r.value}
                </div>
                <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10, marginTop: 4 }}>{r.hint}</div>
              </div>
            </div>
          ))}

          {/* Accent hue picker — single source of truth shared with TweaksPanel */}
          <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 14, padding: '14px 0' }}>
            <div className="t-label">ACCENT HUE</div>
            <div>
              <div style={{ display: 'flex', gap: 10 }}>
                {ACCENT_HUES.map((h) => (
                  <button
                    key={h.id}
                    onClick={() => setHue(h.id)}
                    title={h.name}
                    style={{
                      width: 36, height: 36, borderRadius: '50%',
                      background: h.swatch,
                      border: hue === h.id ? `2px solid var(--fg)` : '1px solid var(--line)',
                      boxShadow: hue === h.id ? '0 0 12px ' + h.swatch : 'none',
                      cursor: 'pointer',
                    }}
                  />
                ))}
              </div>
              <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10, marginTop: 6 }}>
                Persisted to localStorage (key: dayz_dash_tweaks_v1)
              </div>
            </div>
          </div>

          <div style={{ marginTop: 18, padding: 12, border: '1px dashed var(--line-hard)', color: 'var(--fg-3)', fontSize: 11 }} className="t-mono">
            STUB · backend URL / endpoint / postgres / interval / model are read-only in this demo. Wire to a real config endpoint when needed.
          </div>
        </div>
      </div>
    </main>
  )
}
