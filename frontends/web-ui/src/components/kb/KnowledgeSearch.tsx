/* Search view: BM25 over the chunks corpus, snippet + score bar. */

import { useEffect, useState } from 'react'
import { useKbSearch } from '../../hooks/useDashboardData'
import { getSourceIcon } from '../icons'

interface Props {
  onSelectSource: (id: string) => void
}

export function KnowledgeSearch({ onSelectSource }: Props) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const id = setTimeout(() => setDebouncedQuery(query.trim()), 250)
    return () => clearTimeout(id)
  }, [query])

  const { data, isLoading } = useKbSearch(debouncedQuery, 25)

  // Listen for global '/' shortcut to focus the search input
  useEffect(() => {
    const onFocus = () => {
      const el = document.getElementById('kb-search-input') as HTMLInputElement | null
      el?.focus()
    }
    window.addEventListener('dashboard:focus-search', onFocus)
    return () => window.removeEventListener('dashboard:focus-search', onFocus)
  }, [])

  const maxScore = data && data.items.length > 0 ? Math.max(...data.items.map((h) => h.score), 0.001) : 1

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--line-soft)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 12px', height: 36, border: '1px solid var(--line)', background: 'var(--bg-inset)' }}>
          <span style={{ color: 'var(--fg-3)', fontSize: 14 }}>⌕</span>
          <input
            id="kb-search-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the corpus — try OnEntityKilled, PlayerBase, RestContext…"
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--fg)',
              fontFamily: 'var(--f-mono)',
              fontSize: 13,
            }}
          />
          {query && (
            <button onClick={() => setQuery('')} className="btn-ghost" style={{ height: 22 }}>×</button>
          )}
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        {!debouncedQuery ? (
          <div className="empty-illo">
            <div className="t-display" style={{ color: 'var(--fg-2)', fontSize: 13 }}>SEARCH THE CORPUS</div>
            <div style={{ fontSize: 11, color: 'var(--fg-4)', maxWidth: 360 }}>
              BM25 ranking over the chunks index. Type a term and we'll surface the most relevant snippets across {`8,201`} chunks.
            </div>
          </div>
        ) : isLoading ? (
          <div className="t-label" style={{ padding: 18 }}>Searching…</div>
        ) : !data || !data.kb_available ? (
          <div style={{ padding: 18, color: 'var(--bad)' }}>KB unreachable.</div>
        ) : data.items.length === 0 ? (
          <div className="empty-illo">
            <div className="t-display" style={{ color: 'var(--fg-2)', fontSize: 13 }}>NO HITS</div>
            <div style={{ fontSize: 11, color: 'var(--fg-4)' }}>Try broader keywords.</div>
          </div>
        ) : (
          <div>
            {data.items.map((h) => {
              const Icon = getSourceIcon(h.source_type)
              const scorePct = Math.min(100, (h.score / maxScore) * 100)
              return (
                <div
                  key={h.chunk_id}
                  onClick={() => onSelectSource(h.source_id)}
                  style={{ padding: '12px 18px', borderBottom: '1px solid var(--line-soft)', cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ color: 'var(--amber)' }}><Icon /></span>
                    <span className="t-mono" style={{ color: 'var(--fg-2)', fontSize: 11 }}>
                      {h.title ?? h.source_url}
                    </span>
                    <span className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 9.5, marginLeft: 'auto' }}>
                      chunk #{h.chunk_index} · {h.source_type}
                    </span>
                  </div>
                  <div style={{ color: 'var(--fg-3)', fontSize: 12, marginBottom: 6, lineHeight: 1.5 }}>
                    {h.snippet}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="bar-track" style={{ flex: 1, maxWidth: 200 }}>
                      <div className="bar-fill" style={{ width: `${scorePct}%` }} />
                    </div>
                    <span className="t-mono" style={{ fontSize: 9.5, color: 'var(--fg-4)' }}>
                      score {h.score.toFixed(3)}
                    </span>
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
