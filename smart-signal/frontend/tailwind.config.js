/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0A0E14',
        panel: '#111723',
        border: '#1E2736',
        'signal-green': '#2EE59D',
        'signal-red': '#FF4D5E',
        'signal-amber': '#FFB020',
        accent: '#3DD6F5',
        muted: '#4A5568',
        'text-primary': '#E2E8F0',
        'text-secondary': '#94A3B8',
      },
      fontFamily: {
        sans: ['"Space Grotesk"', 'Sora', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '6px',
        sm: '4px',
        lg: '8px',
      },
      animation: {
        'pulse-amber': 'pulseAmber 1s ease-in-out infinite',
        'glow-green': 'glowGreen 2s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
        'roll': 'roll 0.3s ease-out',
      },
      keyframes: {
        pulseAmber: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(255, 176, 32, 0.4)' },
          '50%': { boxShadow: '0 0 0 12px rgba(255, 176, 32, 0)' },
        },
        glowGreen: {
          '0%, 100%': { boxShadow: '0 0 8px 2px rgba(46, 229, 157, 0.3)' },
          '50%': { boxShadow: '0 0 16px 6px rgba(46, 229, 157, 0.6)' },
        },
        roll: {
          '0%': { transform: 'translateY(-100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
