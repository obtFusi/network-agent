/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Pipeline status colors
        'status-pending': '#6b7280',
        'status-running': '#3b82f6',
        'status-completed': '#22c55e',
        'status-failed': '#ef4444',
        'status-aborted': '#f59e0b',
        'status-waiting': '#8b5cf6',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
