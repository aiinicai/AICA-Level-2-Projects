/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#f8fafc',
          100: '#f1f5f9',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        orange: {
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
        },
        ca: {
          bg: '#ffffff',
          sidebar: '#0f172a',
          header: '#0f172a',
          accent: '#ea580c',
          card: '#f8fafc',
          border: '#e2e8f0',
          text: '#1e293b',
          muted: '#64748b'
        }
      }
    },
  },
  plugins: [],
}
