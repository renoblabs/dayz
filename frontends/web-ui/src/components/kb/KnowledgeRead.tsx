/* Read view: full content of a single source with chunk boundaries. */

import { useKbSource } from '../../hooks/useDashboardData'
import { getSourceIcon } from '../icons'

interface Props {
  sourceId: string | null
}

export function KnowledgeRead({ sourceId }: Props) {
  const { data, isLoading } = useKbSource(sourceId)

  if (!sourceId) {
    return (
      <div className="empty-illo">
        <div className="t-display" style={{ color: 'var(--fg-2)', fontSize: 13 }}>NO SOURCE SELECTED</div>
        <div style={{ fontSize: 11, color: 'var(--fg-4)', maxWidth: 360 }}>
          Pick a source from Browse or Search to read its chunks.
        </div>
      </div>
    )
  }

  if (isLoading) return <div className="t-label" style={{ padding: 18 }}>Loading source…</div>
  if (!data || !data.kb_available || !data.source) {
    return <div style={{ padding: 18, color: 'var(--bad)' }}>KB unreachable.</div>
  }

  const s = data.source
  const Icon = getSourceIcon(s.source_type)

  return (
    <div className="blueprint-bg" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* meta header */}
      <div style={{ padding: '14px 24px', borderBottom: '1px solid var(--line)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ color: 'var(--amber)' }}><Icon /></span>
          <div style={{ flex: 1 }}>
            <div className="t-display" style={{ color: 'var(--fg)', fontSize: 16 }}>
              {s.title ?? s.url}
            </div>
            <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10.5, letterSpacing: '0.14em', marginTop: 2 }}>
              {s.source_type} · {data.chunk_count} chunks · {(s.cleaned_len / 1024).toFixed(1)}k chars
            </div>
          </div>
        </div>
      </div>

      {/* content with chunk boundaries */}
      <div style={{ flex: 1, overflow: 'auto', padding: '14px 24px' }}>
        {data.chunks.map((c) => (
          <div
            key={c.id}
            style={{
              display: 'grid',
              gridTemplateColumns: '40px 1fr',
              gap: 14,
              padding: '12px 0',
              borderTop: c.chunk_index === 0 ? 'none' : '1px solid var(--line-soft)',
            }}
          >
            <div className="t-mono" style={{ color: 'var(--amber)', fontSize: 10.5, opacity: 0.7, paddingTop: 2 }}>
              #{c.chunk_index}
            </div>
            <pre
              style={{
                margin: 0,
                fontFamily: 'var(--f-mono)',
                fontSize: 12,
                color: 'var(--fg-2)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                lineHeight: 1.55,
              }}
            >
              {c.text}
            </pre>
          </div>
        ))}
      </div>
    </div>
  )
}
