/* Source-type filter sidebar for the Knowledge tab. */

import { getSourceIcon } from '../icons'

const TYPES: { id: string; label: string }[] = [
  { id: 'all',                label: 'ALL' },
  { id: 'github_mod_file',    label: 'GITHUB' },
  { id: 'local_repo',         label: 'PERSONAL' },
  { id: 'bistudio_wiki',      label: 'BI WIKI' },
  { id: 'youtube_transcript', label: 'TRANSCRIPTS' },
  { id: 'community_doc',      label: 'COMMUNITY' },
  { id: 'manual',             label: 'MANUAL' },
  { id: 'yadz_docs',          label: 'YADZ' },
]

interface Props {
  activeType: string
  onChange: (type: string) => void
  mode: 'browse' | 'search' | 'read'
  onModeChange: (mode: 'browse' | 'search' | 'read') => void
}

export function KnowledgeSidebar({ activeType, onChange, mode, onModeChange }: Props) {
  return (
    <aside style={{ width: 220, borderRight: '1px solid var(--line)', background: 'var(--bg-1)', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header" style={{ borderBottom: '1px solid var(--line)' }}>
        <div className="panel-title"><span className="corner" />KNOWLEDGE</div>
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', borderBottom: '1px solid var(--line-soft)' }}>
        {(['browse', 'search', 'read'] as const).map((m) => (
          <button
            key={m}
            onClick={() => onModeChange(m)}
            className="t-display"
            style={{
              padding: '12px 18px',
              background: mode === m ? 'var(--bg-2)' : 'transparent',
              color: mode === m ? 'var(--amber)' : 'var(--fg-3)',
              border: 'none',
              borderBottom: '1px solid var(--line-soft)',
              borderLeft: mode === m ? '2px solid var(--amber)' : '2px solid transparent',
              textAlign: 'left',
              fontSize: 12,
              letterSpacing: '0.18em',
              cursor: 'pointer',
            }}
          >
            {m.toUpperCase()}
          </button>
        ))}
      </nav>

      <div className="t-label" style={{ padding: '12px 18px 6px' }}>SOURCE TYPE</div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {TYPES.map((t) => {
          const Icon = t.id === 'all' ? null : getSourceIcon(t.id)
          const active = activeType === t.id
          return (
            <button
              key={t.id}
              onClick={() => onChange(t.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 18px',
                background: active ? 'var(--amber-soft)' : 'transparent',
                color: active ? 'var(--amber)' : 'var(--fg-3)',
                border: 'none',
                borderLeft: active ? '2px solid var(--amber)' : '2px solid transparent',
                fontFamily: 'var(--f-mono)',
                fontSize: 11,
                letterSpacing: '0.12em',
                textAlign: 'left',
                cursor: 'pointer',
              }}
            >
              {Icon ? <Icon /> : <span style={{ width: 14, display: 'inline-block' }} />}
              {t.label}
            </button>
          )
        })}
      </div>
    </aside>
  )
}
