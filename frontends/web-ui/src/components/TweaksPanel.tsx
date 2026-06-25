/* Floating runtime tweaks panel.
   Toggle: button in lower-right corner OR keyboard shortcut.
   Knobs: Accent hue, Density, Film grain, CRT scanlines.
   Persistence: hue + density only (grain + scanlines reset per design). */

import { useEffect, useState } from 'react'
import { ACCENT_HUES, useTweaks, type Density } from '../state/tweaks'

const DENSITIES: Density[] = ['compact', 'comfortable', 'spacious']

export function TweaksPanel() {
  const { hue, density, grain, scanlines, setHue, setDensity, setGrain, setScanlines, resetDefaults } = useTweaks()
  const [open, setOpen] = useState(false)

  // Toggle with comma key (',' on its own — not "g ," nav)
  // Use shift+comma alone? Conflict with global "g ," nav. Use a button as the primary affordance.
  // Optional: ctrl+. or other combos can be added later.
  useEffect(() => {
    // No-op effect kept for future shortcut additions.
  }, [])

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        className="btn-ghost"
        title="Tweaks · accent / density / grain / scanlines"
        style={{
          position: 'fixed',
          right: 14,
          bottom: 44,
          zIndex: 100,
          height: 32,
          background: 'var(--bg-2)',
          border: '1px solid var(--line-hard)',
        }}
      >
        ◧ TWEAKS
      </button>

      {open && (
        <div
          className="panel tick-corners"
          style={{
            position: 'fixed',
            right: 14,
            bottom: 84,
            width: 320,
            zIndex: 100,
            background: 'var(--bg-1)',
            boxShadow: '0 10px 40px oklch(0 0 0 / 0.6)',
          }}
        >
          <div className="panel-header">
            <div className="panel-title"><span className="corner" />TWEAKS</div>
            <button className="btn-ghost" onClick={() => setOpen(false)} style={{ height: 22 }}>×</button>
          </div>
          <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Accent Hue */}
            <div>
              <div className="t-label" style={{ marginBottom: 6 }}>ACCENT HUE</div>
              <div style={{ display: 'flex', gap: 8 }}>
                {ACCENT_HUES.map((h) => (
                  <button
                    key={h.id}
                    onClick={() => setHue(h.id)}
                    title={h.name}
                    style={{
                      width: 32, height: 32, borderRadius: '50%',
                      background: h.swatch,
                      border: hue === h.id ? '2px solid var(--fg)' : '1px solid var(--line)',
                      boxShadow: hue === h.id ? `0 0 10px ${h.swatch}` : 'none',
                      cursor: 'pointer',
                      flexShrink: 0,
                    }}
                  />
                ))}
              </div>
              <div className="t-mono" style={{ color: 'var(--fg-4)', fontSize: 9.5, marginTop: 4 }}>
                {ACCENT_HUES.find((h) => h.id === hue)?.name}
              </div>
            </div>

            {/* Density */}
            <div>
              <div className="t-label" style={{ marginBottom: 6 }}>DENSITY</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {DENSITIES.map((d) => (
                  <button
                    key={d}
                    onClick={() => setDensity(d)}
                    className={`chip ${density === d ? 'active' : ''}`}
                  >
                    {d.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Film grain */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div className="t-label">FILM GRAIN</div>
                <div className="t-mono" style={{ color: 'var(--fg-3)', fontSize: 10 }}>
                  {(grain * 100).toFixed(0)}%
                </div>
              </div>
              <input
                type="range"
                min={0}
                max={20}
                step={1}
                value={Math.round(grain * 100)}
                onChange={(e) => setGrain(Number(e.target.value) / 100)}
                style={{ width: '100%', marginTop: 6 }}
              />
            </div>

            {/* CRT scanlines */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div className="t-label">CRT SCANLINES</div>
                <div className="t-mono" style={{ color: 'var(--fg-3)', fontSize: 10 }}>
                  {scanlines.toFixed(1)}
                </div>
              </div>
              <input
                type="range"
                min={0}
                max={3}
                step={0.5}
                value={scanlines}
                onChange={(e) => setScanlines(Number(e.target.value))}
                style={{ width: '100%', marginTop: 6 }}
              />
            </div>

            <button
              onClick={resetDefaults}
              className="t-mono"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--fg-3)',
                fontSize: 10.5,
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                textAlign: 'right',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              ↻ RESET TO DEFAULTS
            </button>
          </div>
        </div>
      )}
    </>
  )
}
