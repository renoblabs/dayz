/* ─────────────────────────────────────────────────────────────────
   TopRail — 48px global navigation bar.
   Brand mark, 8 tabs, SSE connection dot, search hint, pause toggle,
   live UTC clock. Sticky-top.
   ───────────────────────────────────────────────────────────────── */

import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { BrandMark } from './icons'

const TABS: { to: string; label: string; kbd: string }[] = [
  { to: '/ops',         label: 'OPS',        kbd: 'g e' },
  { to: '/servers',     label: 'SERVERS',    kbd: 'g s' },
  { to: '/players',     label: 'PLAYERS',    kbd: 'g p' },
  { to: '/encounters',  label: 'ENCOUNTERS', kbd: 'g n' },
  { to: '/trophies',    label: 'TROPHIES',   kbd: 'g t' },
  { to: '/alerts',      label: 'ALERTS',     kbd: 'g a' },
  { to: '/kb',          label: 'KNOWLEDGE',  kbd: 'g k' },
  { to: '/settings',    label: 'SETTINGS',   kbd: 'g ,' },
]

interface TopRailProps {
  isConnected: boolean
  paused: boolean
  onTogglePause: () => void
}

function useUtcClock(): string {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  // YYYY-MM-DD HH:mm:ss UTC
  const pad = (n: number) => String(n).padStart(2, '0')
  const s = `${now.getUTCFullYear()}-${pad(now.getUTCMonth() + 1)}-${pad(now.getUTCDate())} ${pad(now.getUTCHours())}:${pad(now.getUTCMinutes())}:${pad(now.getUTCSeconds())}Z`
  return s
}

export function TopRail({ isConnected, paused, onTogglePause }: TopRailProps) {
  const utc = useUtcClock()
  return (
    <header className="toprail">
      <div className="brand">
        <BrandMark />
        <div>
          <div className="brand-name">DAYZ</div>
          <div className="brand-sub">OPERATOR · NETWORK</div>
        </div>
      </div>

      <nav className="nav">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            className={({ isActive }) => 'nav-tab' + (isActive ? ' active' : '')}
          >
            {t.label}
            <span className="kbd">{t.kbd}</span>
          </NavLink>
        ))}
      </nav>

      <div className="meta">
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <span
            className={'dot ' + (isConnected ? 'ok live' : 'bad')}
            aria-label={isConnected ? 'SSE connected' : 'SSE disconnected'}
          />
          {isConnected ? 'LIVE' : 'OFFLINE'}
        </span>

        <button
          className="btn-ghost"
          onClick={onTogglePause}
          title={paused ? 'Resume event stream' : 'Pause event stream'}
        >
          {paused ? '▶ RESUME' : '❚❚ PAUSE'}
        </button>

        <span className="search">
          <span aria-hidden>⌕</span>
          <span style={{ color: 'var(--fg-3)' }}>SEARCH</span>
          <kbd>/</kbd>
        </span>

        <span className="t-mono" style={{ color: 'var(--fg-2)', fontVariantNumeric: 'tabular-nums' }}>
          {utc}
        </span>
      </div>
    </header>
  )
}
