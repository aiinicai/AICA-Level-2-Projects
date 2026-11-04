/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ivory: {
          50: '#FDFCF9',
          100: '#FAF7F2',
          200: '#F3EFE6',
          300: '#E8E2D5',
          400: '#D7CEBE',
          500: '#BFB29E'
        },
        charcoal: {
          50: '#F6F6F6',
          100: '#E7E7E7',
          700: '#3F3C3A',
          800: '#2A2725',
          900: '#1C1A18',
          950: '#121110'
        },
        gold: {
          50: '#FDFBF5',
          100: '#F9F4E5',
          200: '#EFE2BD',
          300: '#E2CA8B',
          400: '#D1AC56',
          500: '#B88B2A',
          600: '#99701E',
          700: '#7A5618',
          800: '#5F4115',
          900: '#483112'
        },
        silver: {
          50: '#F8F9FA',
          100: '#F1F3F5',
          200: '#E2E6EA',
          300: '#CFD4DA',
          400: '#9BA2AA',
          500: '#6C757D',
          600: '#495057',
          700: '#343A40',
          800: '#212529'
        }
      },
      fontFamily: {
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['"Inter"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace']
      }
    },
  },
  plugins: [],
}
