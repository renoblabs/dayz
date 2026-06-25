/* ═════════════════════════════════════════════════════════════════
   DAYZ OPS · ICONOGRAPHY
   Ported from _design-handoff-staging/.../icons.jsx. SVG with
   currentColor for tint. Stencil/silhouette aesthetic.
   ═════════════════════════════════════════════════════════════════ */

import type { CSSProperties, ReactElement, SVGProps } from 'react'

// ─── BOSS CLASS ICONS ────────────────────────────────────────────
// Keys are boss classnames. `ZmbM_MarksTester` / `ZmbF_BetaQueen` are
// example MarksContent classes. The `ExampleBoss_*` keys are neutral
// placeholders — integrators should substitute the classnames of their
// own boss/content mod (or a licensed third-party boss mod). Any class
// without a matching key falls back to FallbackBoss, so adding or
// renaming keys never breaks rendering.
type IconProps = SVGProps<SVGSVGElement> & { size?: number }

export const BossIcon: Record<string, (p: IconProps) => ReactElement> = {
  ZmbM_MarksTester: ({ size = 14, ...p }) => (
    <svg viewBox="0 0 24 24" width={size} height={size} {...p}>
      <path fill="currentColor" d="M11 2 h2 v3 h-2 z M9 5 h6 v4 h-6 z M7 9 h10 v3 l-3 1 v8 h-2 v-7 h-2 v7 h-2 v-8 l-3 -1 z"/>
    </svg>
  ),
  ExampleBoss_01: ({ size = 14, ...p }) => (
    <svg viewBox="0 0 24 24" width={size} height={size} {...p}>
      <path fill="currentColor" d="M12 2 c-3 0 -5 2 -5 5 v2 h10 v-2 c0 -3 -2 -5 -5 -5 z M6 10 h12 v3 h-2 v9 h-2 v-6 h-4 v6 h-2 v-9 h-2 z"/>
    </svg>
  ),
  ExampleBoss_02: ({ size = 14, ...p }) => (
    <svg viewBox="0 0 24 24" width={size} height={size} {...p}>
      <path fill="currentColor" d="M9 2 l1 2 l1 -2 l1 2 l1 -2 l1 2 l1 -1 v3 h-8 v-3 l1 1 z M7 8 h10 v4 h-10 z M9 13 h6 v9 h-2 v-5 h-2 v5 h-2 z"/>
    </svg>
  ),
  ZmbF_BetaQueen: ({ size = 14, ...p }) => (
    <svg viewBox="0 0 24 24" width={size} height={size} {...p}>
      <circle cx="12" cy="5" r="3" fill="currentColor"/>
      <path fill="currentColor" d="M7 9 h10 v5 l-2 1 l1 7 h-2 l-1 -6 h-2 l-1 6 h-2 l1 -7 l-2 -1 z"/>
    </svg>
  ),
  ExampleBoss_03: ({ size = 14, ...p }) => (
    <svg viewBox="0 0 24 24" width={size} height={size} {...p}>
      <path fill="currentColor" d="M8 2 h8 v2 h1 v3 h-10 v-3 h1 z M5 8 h14 v8 l-3 1 v5 h-2 v-4 h-4 v4 h-2 v-5 l-3 -1 z"/>
    </svg>
  ),
  ExampleBoss_04: ({ size = 14, ...p }) => (
    <svg viewBox="0 0 24 24" width={size} height={size} {...p}>
      <path fill="currentColor" d="M9 2 h6 v3 h2 v3 h-10 v-3 h2 z M3 9 h18 v6 l-4 1 v6 h-2 v-5 h-6 v5 h-2 v-6 l-4 -1 z"/>
    </svg>
  ),
}

const FallbackBoss = ({ size = 14, ...p }: IconProps): ReactElement => (
  <svg viewBox="0 0 24 24" width={size} height={size} {...p}>
    <path fill="currentColor" d="M9 3 h6 v4 h-6 z M7 8 h10 v5 l-2 1 v8 h-2 v-6 h-2 v6 h-2 v-8 l-2 -1 z"/>
  </svg>
)

export function getBossIcon(className: string): (p: IconProps) => ReactElement {
  return BossIcon[className] ?? FallbackBoss
}

// ─── EVENT TYPE GLYPHS ───────────────────────────────────────────
export const EventGlyph: Record<string, (p: IconProps) => ReactElement> = {
  player_connected: (p) => (
    <svg viewBox="0 0 16 16" width={12} height={12} {...p}>
      <path fill="currentColor" d="M2 8 l4 -4 v3 h7 v2 h-7 v3 z"/>
    </svg>
  ),
  player_disconnected: (p) => (
    <svg viewBox="0 0 16 16" width={12} height={12} {...p}>
      <path fill="currentColor" d="M14 8 l-4 -4 v3 h-7 v2 h7 v3 z"/>
    </svg>
  ),
  server_heartbeat: (p) => (
    <svg viewBox="0 0 16 16" width={12} height={12} {...p}>
      <path stroke="currentColor" strokeWidth="1.5" fill="none" d="M1 8 h3 l1 -3 l2 6 l2 -4 l1 1 h5"/>
    </svg>
  ),
  trophy_awarded: (p) => (
    <svg viewBox="0 0 16 16" width={12} height={12} {...p}>
      <path fill="currentColor" d="M4 2 h8 v4 c0 2 -1 3 -3 3 v2 h2 v2 h-6 v-2 h2 v-2 c-2 0 -3 -1 -3 -3 z"/>
    </svg>
  ),
  boss_killed: (p) => (
    <svg viewBox="0 0 16 16" width={12} height={12} {...p}>
      <path fill="currentColor" d="M3 4 l5 4 l5 -4 v8 l-5 -4 l-5 4 z"/>
    </svg>
  ),
  boss_spawned: (p) => (
    <svg viewBox="0 0 16 16" width={12} height={12} {...p}>
      <path fill="currentColor" d="M8 1 l2 4 l4 1 l-3 3 l1 4 l-4 -2 l-4 2 l1 -4 l-3 -3 l4 -1 z"/>
    </svg>
  ),
}

export function getEventGlyph(eventType: string): (p: IconProps) => ReactElement {
  // Map "boss.killed" → "boss_killed" lookup key
  const key = eventType.replace(/\./g, '_')
  return EventGlyph[key] ?? ((_p) => (
    <svg viewBox="0 0 16 16" width={12} height={12}>
      <circle cx="8" cy="8" r="3" fill="currentColor"/>
    </svg>
  ))
}

// ─── PLAYER AVATAR (deterministic-by-name) ───────────────────────
const AVATAR_SHAPES = ['skull', 'helmet', 'gasmask', 'respirator', 'hood'] as const
type AvatarShape = (typeof AVATAR_SHAPES)[number]

function hashStr(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h)
}

interface PlayerAvatarProps {
  name: string
  size?: number
}

export function PlayerAvatar({ name, size = 24 }: PlayerAvatarProps): ReactElement {
  const h = hashStr(name)
  const shape: AvatarShape = AVATAR_SHAPES[h % AVATAR_SHAPES.length]
  const hue = (h * 37) % 360
  const frame = `oklch(0.45 0.04 ${hue})`
  const inner = `oklch(0.22 0.02 ${hue})`
  const wrap: CSSProperties = {
    width: size,
    height: size,
    borderRadius: '50%',
    background: inner,
    border: `1px solid ${frame}`,
    display: 'grid',
    placeItems: 'center',
    flexShrink: 0,
    position: 'relative',
    overflow: 'hidden',
  }
  return (
    <div style={wrap}>
      <svg viewBox="0 0 24 24" width={size - 4} height={size - 4} style={{ color: 'var(--fg-2)' }}>
        {shape === 'skull' && (
          <g fill="currentColor">
            <path d="M12 4 c-4 0 -6 3 -6 6 v4 l2 1 v3 h2 v-2 h4 v2 h2 v-3 l2 -1 v-4 c0 -3 -2 -6 -6 -6 z"/>
            <rect x="9" y="10" width="2" height="2" fill="var(--bg-0)"/>
            <rect x="13" y="10" width="2" height="2" fill="var(--bg-0)"/>
          </g>
        )}
        {shape === 'helmet' && (
          <g fill="currentColor">
            <path d="M5 12 c0 -4 3 -7 7 -7 s7 3 7 7 v3 h-14 z M5 16 h14 v1 h-14 z"/>
          </g>
        )}
        {shape === 'gasmask' && (
          <g fill="currentColor">
            <path d="M6 8 c0 -2 2 -4 6 -4 s6 2 6 4 v8 c0 2 -2 3 -3 3 h-6 c-1 0 -3 -1 -3 -3 z"/>
            <circle cx="9.5" cy="11" r="1.5" fill="var(--bg-0)"/>
            <circle cx="14.5" cy="11" r="1.5" fill="var(--bg-0)"/>
            <rect x="10" y="16" width="4" height="3" fill="var(--bg-0)"/>
          </g>
        )}
        {shape === 'respirator' && (
          <g fill="currentColor">
            <path d="M7 6 h10 v4 h-3 v3 c0 2 -1 4 -2 4 s-2 -2 -2 -4 v-3 h-3 z"/>
            <rect x="11" y="6" width="2" height="3" fill="var(--bg-0)"/>
          </g>
        )}
        {shape === 'hood' && (
          <g fill="currentColor">
            <path d="M12 4 c-5 0 -8 3 -8 8 v4 l2 1 v3 h12 v-3 l2 -1 v-4 c0 -5 -3 -8 -8 -8 z"/>
            <path d="M8 12 h8 v3 h-8 z" fill="var(--bg-0)"/>
          </g>
        )}
      </svg>
    </div>
  )
}

// ─── KB SOURCE TYPE ICONS ───────────────────────────────────────
export const SourceIcon: Record<string, (p: IconProps) => ReactElement> = {
  'bi-wiki': (p) => (
    <svg viewBox="0 0 24 24" width={14} height={14} {...p}>
      <path fill="currentColor" d="M4 4 h7 c1 0 2 1 2 2 v15 c0 -1 -1 -2 -2 -2 h-7 z M20 4 h-7 c-1 0 -2 1 -2 2 v15 c0 -1 1 -2 2 -2 h7 z"/>
    </svg>
  ),
  bistudio_wiki: (p) => SourceIcon['bi-wiki'](p),
  github: (p) => (
    <svg viewBox="0 0 24 24" width={14} height={14} {...p}>
      <path stroke="currentColor" strokeWidth="2" fill="none" d="M9 6 l-5 6 l5 6 M15 6 l5 6 l-5 6"/>
    </svg>
  ),
  github_mod_file: (p) => SourceIcon['github'](p),
  transcript: (p) => (
    <svg viewBox="0 0 24 24" width={14} height={14} {...p}>
      <rect x="3" y="5" width="18" height="14" stroke="currentColor" strokeWidth="1.5" fill="none"/>
      <path fill="currentColor" d="M10 9 l5 3 l-5 3 z"/>
    </svg>
  ),
  youtube_transcript: (p) => SourceIcon['transcript'](p),
  personal: (p) => (
    <svg viewBox="0 0 24 24" width={14} height={14} {...p}>
      <path fill="currentColor" d="M5 3 h11 l4 4 v14 h-15 z M16 3 v4 h4"/>
      <path stroke="var(--bg-0)" strokeWidth="1" d="M8 11 h8 M8 14 h8 M8 17 h5"/>
    </svg>
  ),
  local_repo: (p) => SourceIcon['personal'](p),
  community_doc: (p) => SourceIcon['personal'](p),
  manual: (p) => SourceIcon['personal'](p),
  config: (p) => (
    <svg viewBox="0 0 24 24" width={14} height={14} {...p}>
      <path fill="currentColor" d="M12 2 l1 2 l2 -1 l1 2 l2 1 v2 l2 1 l-1 2 l1 2 l-2 1 v2 l-2 1 l-1 2 l-2 -1 l-1 2 l-1 -2 l-2 1 l-1 -2 l-2 -1 v-2 l-2 -1 l1 -2 l-1 -2 l2 -1 v-2 l2 -1 l1 -2 l2 1 z"/>
      <circle cx="12" cy="12" r="3" fill="var(--bg-0)"/>
    </svg>
  ),
  yadz_docs: (p) => SourceIcon['config'](p),
}

export function getSourceIcon(type: string): (p: IconProps) => ReactElement {
  return SourceIcon[type] ?? SourceIcon['personal']
}

// ─── MAP SILHOUETTES (server backdrops) ──────────────────────────
export const MapSilhouette: Record<string, (p: IconProps) => ReactElement> = {
  chernarusplus: (p) => (
    <svg viewBox="0 0 200 130" preserveAspectRatio="xMidYMid slice" {...p}>
      <path fill="currentColor" opacity="0.6"
        d="M5 60 Q15 40 30 35 Q50 25 80 30 Q110 28 130 38 Q160 40 175 55 Q190 70 185 90 Q175 110 150 115 Q120 122 95 118 Q60 120 35 110 Q15 95 8 80 Z"/>
      <path stroke="currentColor" strokeWidth="0.5" fill="none" opacity="0.3"
        d="M5 60 Q15 40 30 35 Q50 25 80 30"/>
      <circle cx="60" cy="55" r="1.5" fill="currentColor"/>
      <circle cx="100" cy="65" r="1.5" fill="currentColor"/>
      <circle cx="140" cy="80" r="1.5" fill="currentColor"/>
    </svg>
  ),
  livonia: (p) => (
    <svg viewBox="0 0 200 130" preserveAspectRatio="xMidYMid slice" {...p}>
      <path fill="currentColor" opacity="0.6"
        d="M30 30 Q60 20 100 25 Q140 22 170 35 Q185 50 175 75 Q165 100 130 105 Q90 110 60 100 Q30 90 25 70 Q20 50 30 30 Z"/>
      <circle cx="80" cy="55" r="1.5" fill="currentColor"/>
      <circle cx="120" cy="70" r="1.5" fill="currentColor"/>
    </svg>
  ),
  namalsk: (p) => (
    <svg viewBox="0 0 200 130" preserveAspectRatio="xMidYMid slice" {...p}>
      <path fill="currentColor" opacity="0.6"
        d="M90 15 Q105 10 115 20 Q120 35 115 50 Q120 70 110 90 Q105 110 95 115 Q85 110 80 90 Q75 70 80 50 Q75 35 85 20 Z"/>
      <circle cx="98" cy="50" r="1.5" fill="currentColor"/>
      <circle cx="95" cy="80" r="1.5" fill="currentColor"/>
    </svg>
  ),
}

// ─── EMPTY STATE ILLUSTRATIONS ───────────────────────────────────
interface RadarEmptyProps {
  size?: number
}
export function RadarEmpty({ size = 140 }: RadarEmptyProps): ReactElement {
  return (
    <svg viewBox="0 0 200 200" width={size} height={size} style={{ color: 'var(--line-hard)' }}>
      <circle cx="100" cy="100" r="90" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.5"/>
      <circle cx="100" cy="100" r="60" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.4"/>
      <circle cx="100" cy="100" r="30" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.3"/>
      <line x1="100" y1="10" x2="100" y2="190" stroke="currentColor" strokeWidth="0.5" opacity="0.3"/>
      <line x1="10" y1="100" x2="190" y2="100" stroke="currentColor" strokeWidth="0.5" opacity="0.3"/>
      <path d="M100 100 L100 10 A90 90 0 0 1 180 60 Z" fill="var(--amber)" opacity="0.06">
        <animateTransform attributeName="transform" type="rotate" from="0 100 100" to="360 100 100" dur="4s" repeatCount="indefinite"/>
      </path>
      <line x1="100" y1="100" x2="100" y2="10" stroke="var(--amber)" strokeWidth="1" opacity="0.6">
        <animateTransform attributeName="transform" type="rotate" from="0 100 100" to="360 100 100" dur="4s" repeatCount="indefinite"/>
      </line>
      <text x="100" y="125" textAnchor="middle" fill="currentColor" fontSize="10" fontFamily="var(--f-mono)" letterSpacing="2" opacity="0.6">NO SIGNAL</text>
    </svg>
  )
}

// ─── BRAND MARK (top rail sigil) ─────────────────────────────────
// CSS-driven via .brand-mark class in chrome.css; this is just the JSX.
export function BrandMark(): ReactElement {
  return (
    <div className="brand-mark"><span>D</span></div>
  )
}
