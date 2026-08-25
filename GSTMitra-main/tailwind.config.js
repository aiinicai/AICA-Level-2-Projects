/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    fontFamily: {
      sans: ['Montserrat', 'ui-sans-serif', 'system-ui', 'sans-serif'],
    },
    fontWeight: {
      thin: '100',
      extralight: '200',
      light: '300',
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
      extrabold: '800',
      black: '900',
    },
    extend: {
      colors: {
        'dark-bg': '#000000',
        'dark-card': '#101010',
        'dark-border': '#1a1a1a',
        'accent-green': '#00ff88',
        'accent-blue': '#00d4ff',
        'accent-purple': '#8b5cf6',
        'text-primary': '#ffffff',
        'text-secondary': '#a1a1aa',
      },
      boxShadow: {
        'neumorphic-inset': 'inset 4px 4px 8px rgba(0, 0, 0, 0.5), inset -4px -4px 8px rgba(255, 255, 255, 0.05)',
        'neumorphic-raised': '4px 4px 8px rgba(0, 0, 0, 0.5), -4px -4px 8px rgba(255, 255, 255, 0.05)',
        'glow-green': '0 0 20px rgba(0, 255, 136, 0.3)',
        'glow-blue': '0 0 20px rgba(0, 212, 255, 0.3)',
        'glow-purple': '0 0 20px rgba(139, 92, 246, 0.3)',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite alternate',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%': { boxShadow: '0 0 20px rgba(0, 255, 136, 0.3)' },
          '100%': { boxShadow: '0 0 30px rgba(0, 255, 136, 0.6)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [],
}
