/* ─────────────────────────────────────────────────────────────────
   Runtime tweaks: accent hue, density, film grain, CRT scanlines.
   Persists to localStorage; mutates --amber, --grain-opacity, etc.
   on document.documentElement so chrome.css picks up the changes
   without a page reload.

   Hue palette per design directive: 5 entries — Blood Rust (default),
   Infection Green, Hazmat Yellow, Bruise Violet, Amber Classic.
   ───────────────────────────────────────────────────────────────── */

import { useEffect, useState } from 'react'

export type HueId = 'blood-rust' | 'infection-green' | 'hazmat-yellow' | 'bruise-violet' | 'amber-classic'
export type Density = 'compact' | 'comfortable' | 'spacious'

export interface AccentHue {
  id: HueId
  name: string
  swatch: string  // CSS color for picker preview
  amber: string
  amberSoft: string
  amberLine: string
}

export const ACCENT_HUES: AccentHue[] = [
  {
    id: 'blood-rust',
    name: 'Blood Rust (default)',
    swatch: 'oklch(0.62 0.19 28)',
    amber: 'oklch(0.62 0.19 28)',
    amberSoft: 'oklch(0.62 0.19 28 / 0.18)',
    amberLine: 'oklch(0.62 0.19 28 / 0.50)',
  },
  {
    id: 'infection-green',
    name: 'Infection Green',
    swatch: 'oklch(0.68 0.18 145)',
    amber: 'oklch(0.68 0.18 145)',
    amberSoft: 'oklch(0.68 0.18 145 / 0.18)',
    amberLine: 'oklch(0.68 0.18 145 / 0.50)',
  },
  {
    id: 'hazmat-yellow',
    name: 'Hazmat Yellow',
    swatch: 'oklch(0.78 0.16 95)',
    amber: 'oklch(0.78 0.16 95)',
    amberSoft: 'oklch(0.78 0.16 95 / 0.18)',
    amberLine: 'oklch(0.78 0.16 95 / 0.50)',
  },
  {
    id: 'bruise-violet',
    name: 'Bruise Violet',
    swatch: 'oklch(0.58 0.17 305)',
    amber: 'oklch(0.58 0.17 305)',
    amberSoft: 'oklch(0.58 0.17 305 / 0.18)',
    amberLine: 'oklch(0.58 0.17 305 / 0.50)',
  },
  {
    id: 'amber-classic',
    name: 'Amber Classic',
    swatch: '#d97e2b',
    amber: '#d97e2b',
    amberSoft: 'rgba(217,126,43,0.18)',
    amberLine: 'rgba(217,126,43,0.50)',
  },
]

export interface TweaksState {
  hue: HueId
  density: Density
  grain: number       // 0–0.20 (multiplied by 100 in UI for slider 0–20)
  scanlines: number   // 0–3
}

const KEY = 'dayz_dash_tweaks_v1'

const DEFAULTS: TweaksState = {
  hue: 'blood-rust',
  density: 'comfortable',
  grain: 0.06,
  scanlines: 1,
}

function load(): TweaksState {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { ...DEFAULTS }
    const parsed = JSON.parse(raw) as Partial<TweaksState>
    return {
      hue:       (parsed.hue ?? DEFAULTS.hue) as HueId,
      density:   (parsed.density ?? DEFAULTS.density) as Density,
      // Grain + scanlines reset to defaults per README — they were prototype tuning knobs
      grain:     DEFAULTS.grain,
      scanlines: DEFAULTS.scanlines,
    }
  } catch {
    return { ...DEFAULTS }
  }
}

function persist(s: TweaksState) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ hue: s.hue, density: s.density }))
  } catch {
    /* ignore */
  }
}

function applyDom(s: TweaksState) {
  const root = document.documentElement
  const hue = ACCENT_HUES.find((h) => h.id === s.hue) ?? ACCENT_HUES[0]
  root.style.setProperty('--amber', hue.amber)
  root.style.setProperty('--amber-soft', hue.amberSoft)
  root.style.setProperty('--amber-line', hue.amberLine)
  root.style.setProperty('--grain-opacity', s.grain.toFixed(3))
  root.style.setProperty('--glow-strength', s.scanlines.toString())
  // Density multiplier (scales paddings ±25% via panel-level inline style if needed)
  const densityMult = s.density === 'compact' ? 0.75 : s.density === 'spacious' ? 1.25 : 1.0
  root.style.setProperty('--density-mult', densityMult.toString())
  root.dataset.density = s.density
}

// Module-level subscription so multiple components share state without re-running the effect.
type Listener = (s: TweaksState) => void
const listeners = new Set<Listener>()
let current: TweaksState = load()
applyDom(current)

function setState(next: TweaksState) {
  current = next
  applyDom(current)
  persist(current)
  listeners.forEach((l) => l(current))
}

export function useTweaks() {
  const [s, setS] = useState<TweaksState>(current)

  useEffect(() => {
    const l: Listener = (next) => setS(next)
    listeners.add(l)
    return () => {
      listeners.delete(l)
    }
  }, [])

  return {
    hue:       s.hue,
    density:   s.density,
    grain:     s.grain,
    scanlines: s.scanlines,
    setHue:       (h: HueId)       => setState({ ...current, hue: h }),
    setDensity:   (d: Density)     => setState({ ...current, density: d }),
    setGrain:     (g: number)      => setState({ ...current, grain: Math.max(0, Math.min(0.20, g)) }),
    setScanlines: (n: number)      => setState({ ...current, scanlines: Math.max(0, Math.min(3, n)) }),
    resetDefaults: ()              => setState({ ...DEFAULTS }),
  }
}
