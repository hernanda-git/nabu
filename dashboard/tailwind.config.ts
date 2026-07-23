import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        nabu: {
          bg: '#0a0a0f',
          bgSecondary: '#14141f',
          bgTertiary: '#1c1c2e',
          border: '#2a2a3e',
          text: '#e8e8f0',
          textSecondary: '#8888a0',
          accent: {
            green: '#22c55e',
            yellow: '#eab308',
            orange: '#f97316',
            red: '#ef4444',
            blue: '#3b82f6',
          },
          score: {
            high: '#22c55e',
            mid: '#eab308',
            low: '#f97316',
            trash: '#ef4444',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2s linear infinite',
      },
    },
  },
  plugins: [],
}

export default config