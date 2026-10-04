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
        hearth: {
          bg: '#0F1117',
          surface: '#1A1D27',
          border: '#2A2E3D',
          amber: '#F59E0B',
          amberDim: '#78350F',
          gold: '#FBBF24',
          accent: '#38BDF8',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        dyslexic: ['OpenDyslexic', 'Comic Sans MS', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
