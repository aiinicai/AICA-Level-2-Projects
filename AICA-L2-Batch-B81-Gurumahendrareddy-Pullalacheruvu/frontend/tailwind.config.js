/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Brand / sequential navy ramp. This is the ONLY hue used for data
        // marks — the spec says colour means status and nothing else, so the
        // charts are monochrome unless a value has crossed a threshold.
        navy: {
          50:  '#f2f4fd', 100: '#dde2f9', 200: '#b9c2ef', 300: '#8b98e2',
          400: '#5566d0', 500: '#3d4bb5', 600: '#2c3690', 700: '#1e2761',
          800: '#161c49', 900: '#0f1433',
        },
        ink:    { DEFAULT: '#0f172a', soft: '#334155', muted: '#64748b', faint: '#94a3b8' },
        line:   { DEFAULT: '#e2e8f0', soft: '#eef2f7', strong: '#cbd5e1' },
        canvas: '#f6f7fb',
        // Status — validated: all >= 3:1 on white, CVD-separated, normal-vision
        // separated. Grey is deliberately achromatic: it means "don't rely on this".
        red:    { DEFAULT: '#b3261e', bg: '#fef3f2', line: '#fbd5d1' },
        amber:  { DEFAULT: '#a87c00', bg: '#fffaeb', line: '#fbe6a2' },
        green:  { DEFAULT: '#0f7a43', bg: '#ecfdf3', line: '#b7ebcd' },
        grey:   { DEFAULT: '#788699', bg: '#f4f6f8', line: '#dfe4ea' },
        // Diverging poles for waterfalls. Polarity, not status — deliberately
        // chosen so neither pole can be mistaken for a status colour.
        pole:   { pos: '#0f766e', neg: '#6d3fa0', mid: '#e7e9ef' },
      },
      fontFamily: {
        // Local fonts only — the app has to work on a machine with no network.
        sans: ['Inter', 'Segoe UI Variable', 'Segoe UI', 'system-ui',
               '-apple-system', 'Roboto', 'Helvetica Neue', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['11px', { lineHeight: '15px', letterSpacing: '0.02em' }],
      },
      boxShadow: {
        card: '0 1px 2px rgba(15,23,42,0.04), 0 1px 3px rgba(15,23,42,0.03)',
        pop:  '0 10px 30px rgba(15,23,42,0.12), 0 2px 8px rgba(15,23,42,0.06)',
        rail: '1px 0 0 rgba(15,23,42,0.06)',
      },
      keyframes: {
        in:  { '0%': { opacity: 0, transform: 'translateY(4px)' }, '100%': { opacity: 1, transform: 'none' } },
        slide: { '0%': { transform: 'translateX(100%)' }, '100%': { transform: 'none' } },
      },
      animation: { in: 'in .18s ease-out both', slide: 'slide .22s cubic-bezier(.2,.8,.2,1) both' },
    },
  },
  plugins: [],
}
