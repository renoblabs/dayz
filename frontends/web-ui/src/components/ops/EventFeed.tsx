import { useMemo, useState } from 'react'
import { useSharedEventStream } from '../../hooks/eventStreamContext'
import { eventCategory, fmtAgo, summarizeEvent } from '../../lib/format'
import { getBossIcon, getEventGlyph, RadarEmpty } from '../icons'

const FILTERS = [
  { id: 'all',    label: 'ALL',         match: (_e: { event_type: string }) => true },
  { id: 'boss',   label: 'BOSS',        match: (e: { event_type: string }) => e.event_type.startsWith('boss') },
  { id: 'player', label: 'PLAYERS',     match: (e: { event_type: string }) => e.event_type.startsWith('player') },
  { id: 'server', label: 'SERVER',      match: (e: { event_type: string }) => e.event_type.startsWith('server') || e.event_type.startsWith('trophy') },
] as const

type FilterId = typeof FILTERS[number]['id']

export function EventFeed() {
  const { events, isConnected, paused, togglePause } = useSharedEventStream()
  const [filter, setFilter] = useState<FilterId>('all')
  const [expanded, setExpanded] = useState<string | null>(null)

  const counts = useMemo(() => {
    const c = { all: events.length, boss: 0, player: 0, server: 0 } as Record<FilterId, number>
    for (const e of events) {
      const cat = eventCategory(e.event_type)
      if (cat === 'boss') c.boss++
      else if (cat === 'player') c.player++
      else c.server++
    }
    return c
  }, [events])

  const visible = events.filter(FILTERS.find((f) => f.id === filter)!.match)

  const live = isConnected && !paused

  return (
    <div className="panel tick-corners live-region" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 420 }}>
      <div className="panel-header">
        <div className="panel-title">
          <span className="corner" />
          <span>Event Feed</span>
          <span className={`dot ${live ? 'amber live' : 'idle'}`} style={{ marginLeft: 6 }} />
          <span className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10, letterSpacing: '0.16em' }}>
            {live ? 'SSE · STREAMING' : paused ? 'PAUSED' : 'OFFLINE'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn-ghost" onClick={togglePause}>
            {paused ? '▶ RESUME' : '❚❚ PAUSE'}
          </button>
        </div>
      </div>

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: 6, padding: '10px 14px', borderBottom: '1px solid var(--line-soft)', background: 'var(--bg-1)' }}>
        {FILTERS.map((f) => (
          <button
            key={f.id}
            className={`chip ${filter === f.id ? 'active' : ''}`}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
            <span className="count">{counts[f.id]}</span>
          </button>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="t-mono" style={{ fontSize: 9.5, color: 'var(--fg-4)', letterSpacing: '0.14em' }}>
            {visible.length} SHOWN · {events.length} TOTAL
          </span>
        </div>
      </div>

      {/* Feed */}
      <div style={{ flex: 1, overflowY: 'auto', background: 'var(--bg-inset)', minHeight: 280 }}>
        {visible.length === 0 ? (
          <div className="empty-illo">
            <RadarEmpty size={140} />
            <div className="t-display" style={{ color: 'var(--fg-2)', fontSize: 13 }}>NO SIGNAL</div>
            <div style={{ fontSize: 11, color: 'var(--fg-4)', maxWidth: 320 }}>
              Fire one in-game (kill a boss, connect a player, restart server) to see this update.
            </div>
          </div>
        ) : (
          <div>
            {visible.map((e) => (
              <EventRow
                key={e.id}
                event={e}
                expanded={expanded === e.id}
                onToggle={() => setExpanded(expanded === e.id ? null : e.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface RowProps {
  event: { id: string; event_type: string; server_id: string; received_at: string; data?: Record<string, unknown>; __fresh?: boolean }
  expanded: boolean
  onToggle: () => void
}
function EventRow({ event, expanded, onToggle }: RowProps) {
  const cat = eventCategory(event.event_type)
  const summary = summarizeEvent(event.event_type, event.data ?? {})
  const data = event.data ?? {}

  let LeftIcon: ((p: { size?: number }) => React.ReactElement) | null = null
  if (event.event_type.startsWith('boss') && typeof data.boss_display_name === 'string') {
    LeftIcon = getBossIcon(data.boss_display_name as string)
  } else {
    LeftIcon = getEventGlyph(event.event_type)
  }

  const catColor: Record<typeof cat, string> = {
    boss:    'var(--amber)',
    player:  'var(--info)',
    server:  'var(--ok)',
    trophy:  'var(--warn)',
    other:   'var(--fg-3)',
  }
  const color = catColor[cat]

  return (
    <div
      className={'event-row' + (event.__fresh ? ' fresh' : '')}
      onClick={onToggle}
      style={{
        display: 'grid',
        gridTemplateColumns: '24px 80px 100px 1fr 80px',
        gap: 10,
        alignItems: 'center',
        padding: '8px 14px',
        borderBottom: '1px solid var(--line-soft)',
        cursor: 'pointer',
        color: 'var(--fg-2)',
        fontSize: 12,
      }}
    >
      <span style={{ color, display: 'inline-flex' }}>
        {LeftIcon ? <LeftIcon size={14} /> : null}
      </span>
      <span className="t-mono" style={{ color, fontSize: 10.5, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
        {event.event_type}
      </span>
      <span className="t-mono" style={{ color: 'var(--fg-3)', fontSize: 11 }}>
        {event.server_id}
      </span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: expanded ? 'normal' : 'nowrap' }}>
        {summary}
        {expanded && (
          <pre className="t-mono" style={{ marginTop: 6, padding: 8, background: 'var(--bg-0)', border: '1px solid var(--line-soft)', fontSize: 10.5, color: 'var(--fg-3)', overflowX: 'auto' }}>
            {JSON.stringify(data, null, 2)}
          </pre>
        )}
      </span>
      <span className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 10, textAlign: 'right' }}>
        {fmtAgo(event.received_at)}
      </span>
    </div>
  )
}
