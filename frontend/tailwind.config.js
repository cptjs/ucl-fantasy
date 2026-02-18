/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ucl: {
          dark: '#0a1128',
          blue: '#1a237e',
          accent: '#00e5ff',
          gold: '#ffd700',
          green: '#00c853',
          red: '#ff1744',
        }
      }
    },
  },
  plugins: [],
}
