/** @type {import('tailwindcss').Config} */
// Design tokens are the SOURCE OF TRUTH from
// _design-handoff-staging/.../styles.css (oklch values).
// The README's hex block is stale — do not use it.
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Surface tones — cold dead concrete with a faint infection-green wash
        bg: {
          0:     "oklch(0.14 0.010 165)",
          1:     "oklch(0.18 0.012 165)",
          2:     "oklch(0.22 0.014 165)",
          3:     "oklch(0.26 0.014 165)",
          inset: "oklch(0.11 0.008 165)",
        },
        // Bruised lines — cold green-grey
        line: {
          DEFAULT: "oklch(0.30 0.018 165)",
          soft:    "oklch(0.24 0.014 165)",
          hard:    "oklch(0.40 0.025 165)",
        },
        // Text — bone, slightly cool & sickly
        fg: {
          DEFAULT: "oklch(0.92 0.008 110)",
          2:       "oklch(0.78 0.012 130)",
          3:       "oklch(0.60 0.014 145)",
          4:       "oklch(0.46 0.016 155)",
        },
        // Accent — blood rust. The only saturated voice.
        amber: {
          DEFAULT: "oklch(0.62 0.19 28)",
          soft:    "oklch(0.62 0.19 28 / 0.18)",
          line:    "oklch(0.62 0.19 28 / 0.50)",
        },
        // Status semantics
        ok:   "oklch(0.74 0.16 150)",
        warn: "oklch(0.78 0.15 90)",
        bad:  "oklch(0.62 0.21 22)",
        info: "oklch(0.68 0.10 210)",
        idle: "oklch(0.46 0.016 155)",
      },
      fontFamily: {
        display: ['Oswald', 'Bebas Neue', 'ui-sans-serif', 'system-ui'],
        body:    ['Inter', 'ui-sans-serif', 'system-ui'],
        mono:    ['JetBrains Mono', 'IBM Plex Mono', 'ui-monospace', 'SF Mono', 'Menlo', 'monospace'],
      },
      fontSize: {
        // Small mono/label sizes used by panels (10–11px range)
        '2xs':   ['9.5px',  { lineHeight: '1.4' }],
        'xxs':   ['10px',   { lineHeight: '1.4' }],
        'xxxs':  ['10.5px', { lineHeight: '1.4' }],
      },
      letterSpacing: {
        'tight-stencil': '0.06em',
        'stencil':       '0.14em',
        'wide-stencil':  '0.18em',
        'mono-tight':    '0.10em',
        'mono-wide':     '0.12em',
      },
      borderRadius: {
        sm: '2px',
        DEFAULT: '3px',
        md: '3px',
        lg: '4px',
      },
      spacing: {
        '4.5': '18px',
      },
    },
  },
  plugins: [],
}
