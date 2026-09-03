/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        finance: {
          950: '#070B14',
          900: '#0B0F19',
          850: '#0F1626',
          800: '#111827',
          750: '#151F32',
          700: '#1F2937',
          600: '#374151',
          500: '#6B7280',
          400: '#9CA3AF',
          300: '#D1D5DB',
          200: '#E5E7EB',
          100: '#F3F4F6',
          50: '#F9FAFB',
          accent: '#2563EB',
          accentLight: '#3B82F6',
          accentGlow: 'rgba(37, 99, 235, 0.15)',
          green: '#10B981',
          greenLight: '#34D399',
          greenBg: 'rgba(16, 185, 129, 0.12)',
          red: '#EF4444',
          redLight: '#F87171',
          redBg: 'rgba(239, 68, 68, 0.12)',
          amber: '#F59E0B',
          amberBg: 'rgba(245, 158, 11, 0.12)',
          purple: '#8B5CF6',
          cyan: '#06B6D4'
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif']
      }
    },
  },
  plugins: [],
}
