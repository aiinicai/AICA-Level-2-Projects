/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef4fb',
          100: '#d6e4f5',
          500: '#2f5f96',
          600: '#26507f',
          700: '#1e3a5f',
          800: '#172c48',
        },
      },
    },
  },
  plugins: [],
};
