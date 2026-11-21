/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary Corporate Navy/Slate: #1b2632 (C: 84%, M: 72%, Y: 54%, K: 62%)
        brand: {
          50: '#f2f5f8',
          100: '#e2e8ee',
          200: '#c4d1dc',
          300: '#9fb3c5',
          400: '#6b88a3',
          500: '#476684',
          600: '#354d65',
          700: '#2a3c4f',
          800: '#212f3e',
          900: '#1b2632', // User Primary CMYK (84, 72, 54, 62)
          950: '#111820',
        },
        // Secondary Warm Terracotta / Rust: #a45139 (C: 26%, M: 76%, Y: 82%, K: 17%)
        accent: {
          50: '#fdf6f4',
          100: '#faece7',
          200: '#f5d7cf',
          300: '#ebb9ab',
          400: '#dd907a',
          500: '#c3694f',
          600: '#a45139', // User Secondary CMYK (26, 76, 82, 17)
          700: '#863e2a',
          800: '#6e3424',
          900: '#5a2c20',
          950: '#32140d',
          DEFAULT: '#a45139',
        },
        terracotta: {
          50: '#fdf6f4',
          100: '#faece7',
          200: '#f5d7cf',
          300: '#ebb9ab',
          400: '#dd907a',
          500: '#c3694f',
          600: '#a45139',
          700: '#863e2a',
          800: '#6e3424',
          900: '#5a2c20',
          950: '#32140d',
          DEFAULT: '#a45139',
        },
      },
    },
  },
  plugins: [],
}
