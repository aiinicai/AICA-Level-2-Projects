/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#20242B',
        graphite: '#2B3038',
        stone: '#EDE8DD',
        paper: '#FFFFFF',
        verdigris: {
          DEFAULT: '#4C8577',
          soft: '#E4EEEC',
        },
        clay: {
          DEFAULT: '#B5654A',
          soft: '#F3E6DF',
        },
        slate: '#6B7280',
        mist: '#9AA1AC',
        line: '#DCD7CB',
      },
      fontFamily: {
        heading: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      borderRadius: {
        lg: '8px',
      },
    },
  },
  plugins: [],
}
