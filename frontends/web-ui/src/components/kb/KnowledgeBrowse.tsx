/* Browse view: paginated source list, filter by source_type. */

import { useKbSources } from '../../hooks/useDashboardData'
import { fmtAgo } from '../../lib/format'
import { getSourceIcon } from '../icons'

interface Props {
  type: string
  page: number
  onPage: (p: number) => void
  onSelect: (id: string) => void
}

const PAGE_SIZE = 50

export function KnowledgeBrowse({ type, page, onPage, onSelect }: Props) {
  const apiType = type === 'all' ? undefined : type
  const { data, isLoading, error } = useKbSources({ type: apiType, page, page_size: PAGE_SIZE })

  if (isLoading) return <div className="t-label" style={{ padding: 18 }}>Loading…</div>
  if (error) return <div style={{ padding: 18, color: 'var(--bad)' }}>KB unreachable.</div>
  if (!data || !data.kb_available) {
    return (
      <div style={{ padding: 24 }}>
        <div className="t-display" style={{ color: 'var(--fg-2)', fontSize: 14 }}>KB OFFLINE</div>
        <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 11, marginTop: 6 }}>
          Knowledge base postgres unreachable. Try `docker start dayz-stack-postgres`.
        </div>
      </div>
    )
  }

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', padding: '10px 18px', borderBottom: '1px solid var(--line-soft)' }}>
        <div className="t-mono" style={{ color: 'var(--fg-3)', fontSize: 11 }}>
          {data.total.toLocaleString()} sources · page {page} of {totalPages}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button className="btn-ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>‹ PREV</button>
          <button className="btn-ghost" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>NEXT ›</button>
          <button className="btn-ghost" disabled title="// stub: backend write paths not wired">CREATE</button>
          <button className="btn-ghost" disabled title="// stub: backend write paths not wired">REINDEX</button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ position: 'sticky', top: 0, background: 'var(--bg-1)', zIndex: 1 }}>
              {['', 'TITLE', 'TYPE', 'CHUNKS', 'UPDATED', 'SIZE'].map((h, i) => (
                <th
                  key={i}
                  style={{
                    textAlign: 'left',
                    padding: '8px 14px',
                    fontFamily: 'var(--f-mono)',
                    fontSize: 10,
                    letterSpacing: '0.18em',
                    color: 'var(--fg-4)',
                    textTransform: 'uppercase',
                    borderBottom: '1px solid var(--line)',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.items.map((s) => {
              const Icon = getSourceIcon(s.source_type)
              return (
                <tr
                  key={s.id}
                  onClick={() => onSelect(s.id)}
                  style={{ cursor: 'pointer', borderBottom: '1px solid var(--line-soft)' }}
                >
                  <td style={{ padding: '6px 14px', color: 'var(--amber)', width: 24 }}><Icon /></td>
                  <td style={{ padding: '6px 14px', color: 'var(--fg-2)', maxWidth: 480, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {s.title || s.url}
                  </td>
                  <td style={{ padding: '6px 14px' }} className="t-mono">
                    <span style={{ color: 'var(--fg-3)', fontSize: 10.5 }}>{s.source_type}</span>
                  </td>
                  <td style={{ padding: '6px 14px', color: 'var(--fg-3)' }} className="t-mono">—</td>
                  <td style={{ padding: '6px 14px', color: 'var(--fg-3)' }} className="t-mono">{fmtAgo(s.fetched_at)}</td>
                  <td style={{ padding: '6px 14px', color: 'var(--fg-3)' }} className="t-mono">
                    {s.text_len != null ? `${(s.text_len / 1024).toFixed(1)}k` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
