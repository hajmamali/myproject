/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Persian-friendly font stack
        sans: ['Vazirmatn', 'Tahoma', 'Arial', 'sans-serif'],
      },
      colors: {
        // Formal palette for legal UI
        primary: {
          50: '#f3f6fa',
          100: '#e3e9f2',
          200: '#c5d2e5',
          300: '#9fb4d1',
          400: '#6b8db7',
          500: '#476b9a',
          600: '#365682',
          700: '#2c466a',
          800: '#243a58',
          900: '#1b2c43',
        },
        accent: {
          50: '#faf8f3',
          100: '#f2ede3',
          200: '#e5dbc7',
          300: '#d4c5a3',
          400: '#c4b08a',
          500: '#a89570',
          600: '#8d7a5c',
          700: '#73604a',
          800: '#5e4e3d',
          900: '#4c3f32',
        },
      },
    },
  },
  plugins: [],
}
