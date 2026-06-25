import { useEffect, useMemo, useState } from 'react'
import { usePlayers } from '../hooks/useDashboardData'
import { PlayerAvatar } from '../components/icons'
import { fmtAgo } from '../lib/format'

type FilterMode = 'all' | 'online' | 'flagged'

export default function PlayersPage() {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<FilterMode>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data: players = [], isLoading } = usePlayers()

  // Listen for the global '/' shortcut
  useEffect(() => {
    const onFocus = () => {
      const el = document.getElementById('players-search') as HTMLInputElement | null
      el?.focus()
    }
    window.addEventListener('dashboard:focus-search', onFocus)
    return () => window.removeEventListener('dashboard:focus-search', onFocus)
  }, [])

  const filtered = useMemo(() => {
    return players.filter((p) => {
      if (filter === 'online' && p.status !== 'online') return false
      if (filter === 'flagged' && !p.flagged) return false
      if (query && !p.name.toLowerCase().includes(query.toLowerCase()) && !p.steam_id.includes(query)) return false
      return true
    })
  }, [players, query, filter])

  const selected = useMemo(() => {
    if (!selectedId) return filtered[0] || null
    return players.find((p) => p.steam_id === selectedId) || filtered[0] || null
  }, [players, filtered, selectedId])

  if (isLoading && players.length === 0) {
    return (
      <div className="panel-body t-label" style={{ padding: 40, textAlign: 'center' }}>
        LOADING ROSTER...
      </div>
    )
  }

  return (
    <main className="stack-on-mobile" style={{ padding: 16, display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 360px', gap: 16, alignItems: 'start' }}>
      {/* Roster */}
      <div className="panel tick-corners">
        <div className="panel-header">
          <div className="panel-title">
            <span className="corner" />ROSTER
          </div>
        </div>

        {/* Search + filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: '1px solid var(--line-soft)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '0 10px', height: 30, border: '1px solid var(--line)', background: 'var(--bg-inset)', flex: 1, maxWidth: 360 }}>
            <span style={{ color: 'var(--fg-3)' }}>⌕</span>
            <input
              id="players-search"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="search name or steam id"
              style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: 'var(--fg)', fontFamily: 'var(--f-mono)', fontSize: 12 }}
            />
            <kbd className="kbd">/</kbd>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {(['all', 'online', 'flagged'] as const).map((f) => (
              <button key={f} className={`chip ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div style={{ overflow: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr>
                {['', 'PLAYER', 'STATUS', 'KILLS', 'HOURS', 'LAST SEEN', 'JOINED'].map((h, i) => (
                  <th key={i} style={{ textAlign: 'left', padding: '8px 14px', fontFamily: 'var(--f-mono)', fontSize: 10, letterSpacing: '0.18em', color: 'var(--fg-4)', borderBottom: '1px solid var(--line)' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--fg-4)' }} className="t-mono">
                    NO PLAYERS FOUND
                  </td>
                </tr>
              )}
              {filtered.map((p) => (
                <tr
                  key={p.steam_id}
                  onClick={() => setSelectedId(p.steam_id)}
                  style={{
                    cursor: 'pointer',
                    background: selected?.steam_id === p.steam_id ? 'var(--bg-2)' : 'transparent',
                    borderBottom: '1px solid var(--line-soft)',
                  }}
                >
                  <td style={{ padding: '6px 14px', width: 32 }}><PlayerAvatar name={p.name} size={24} /></td>
                  <td style={{ padding: '6px 14px' }} className="t-mono">
                    <span style={{ color: 'var(--fg)', fontSize: 11.5 }}>{p.name}</span>
                    {p.flagged && <span className="chip active" style={{ marginLeft: 8, height: 18, padding: '0 6px', borderColor: 'var(--bad)', color: 'var(--bad)', background: 'oklch(0.62 0.21 22 / 0.12)' }}>FLAGGED</span>}
                  </td>
                  <td style={{ padding: '6px 14px' }} className="t-mono">
                    <span className={`dot ${p.status === 'online' ? 'ok live' : 'idle'}`} style={{ marginRight: 6 }} />
                    <span style={{ color: 'var(--fg-3)', fontSize: 10.5, letterSpacing: '0.12em' }}>{p.status.toUpperCase()}</span>
                  </td>
                  <td style={{ padding: '6px 14px', color: 'var(--fg-2)' }} className="t-num">{p.boss_kills}</td>
                  <td style={{ padding: '6px 14px', color: 'var(--fg-2)' }} className="t-num">{p.hours}</td>
                  <td style={{ padding: '6px 14px', color: 'var(--fg-3)' }} className="t-mono">
                    {fmtAgo(p.last_seen)}
                  </td>
                  <td style={{ padding: '6px 14px', color: 'var(--fg-3)' }} className="t-mono">{fmtAgo(p.joined_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Profile drawer */}
      <aside className="panel tick-corners" style={{ position: 'sticky', top: 64 }}>
        <div className="panel-header">
          <div className="panel-title"><span className="corner" />PROFILE</div>
        </div>
        {!selected ? (
          <div className="panel-body t-label">No player selected.</div>
        ) : (
          <div className="panel-body">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <PlayerAvatar name={selected.name} size={84} />
              <div>
                <div className="t-display" style={{ color: 'var(--fg)', fontSize: 22 }}>{selected.name}</div>
                <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10.5 }}>{selected.steam_id}</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 18 }}>
              <div>
                <div className="t-label">STATUS</div>
                <div className="t-display" style={{ color: selected.status === 'online' ? 'var(--ok)' : 'var(--idle)', fontSize: 14 }}>{selected.status.toUpperCase()}</div>
              </div>
              <div>
                <div className="t-label">CURRENT</div>
                <div className="t-mono" style={{ color: 'var(--fg-2)', fontSize: 11 }}>{selected.current_server_id ?? '—'}</div>
              </div>
              <div>
                <div className="t-label">BOSS KILLS</div>
                <div className="t-num" style={{ color: 'var(--fg)', fontSize: 16 }}>{selected.boss_kills}</div>
              </div>
              <div>
                <div className="t-label">HOURS</div>
                <div className="t-num" style={{ color: 'var(--fg)', fontSize: 16 }}>{selected.hours}</div>
              </div>
            </div>

            <div className="divider-h" />

            <div className="t-label" style={{ marginBottom: 8, opacity: 0.5 }}>STATS (EXPERIMENTAL)</div>
            <div style={{ color: 'var(--fg-4)', fontSize: 11 }} className="t-mono">
                Historical session tracking pending mod update.
            </div>
          </div>
        )}
      </aside>
    </main>
  )
}
