/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Legacy colors (keep for backward compatibility during migration)
        'game-bg': '#1a1a2e',
        'game-card': '#16213e',
        'game-accent': '#0f3460',
        'game-highlight': '#e94560',
        
        // GGLTCG Design System Colors
        'ggltcg': {
          // Primary Colors
          black: '#1A1A1A',
          cream: '#F5F0E8',
          gray: '#8B8680',
          
          // Card Accent Colors (borders, cost indicators)
          red: '#C74444',
          blue: '#5B7FA8',
          purple: '#8B5FA8',
          brown: '#8B6F47',
          
          // UI Colors
          'ui-dark-bg': '#1A1F3A',
          'ui-card-bg': '#2A3556',
          'ui-highlight': '#4A7BFF',
          'ui-toy-badge': '#4A7BFF',
          'ui-action-badge': '#C850FF',
        },
      },
      fontFamily: {
        'bangers': ['Bangers', 'Impact', 'sans-serif'],
        'lato': ['Lato', 'Arial', 'sans-serif'],
      },
      scale: {
        '145': '1.45',  // For small cards (120px)
        '200': '2.00',  // For medium cards (165px)
        '400': '4.00',  // For large preview cards (330px)
      },
      spacing: {
        // Card dimensions based on 825×1125 base
        'card-base-w': '825px',
        'card-base-h': '1125px',
        'card-small-w': '120px',
        'card-small-h': '164px',
        'card-medium-w': '165px',
        'card-medium-h': '225px',
        'card-large-w': '330px',
        'card-large-h': '450px',
      },
    },
  },
  plugins: [],
}
