/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'fraud-red': '#ef4444',
        'fraud-green': '#22c55e',
        'fraud-yellow': '#eab308',
        'fraud-blue': '#3b82f6',
        'surface': '#111827',
        'surface-light': '#1f2937',
        'surface-border': '#374151',
      },
    },
  },
  plugins: [],
}
