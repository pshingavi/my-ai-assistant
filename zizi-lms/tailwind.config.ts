import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0f',
        card: '#13131a',
        'card-hover': '#1a1a24',
        purple: {
          DEFAULT: '#8b5cf6',
          dim: 'rgba(139,92,246,0.2)',
          glow: 'rgba(139,92,246,0.4)',
        },
        cyan: {
          DEFAULT: '#22d3ee',
          dim: 'rgba(34,211,238,0.2)',
          glow: 'rgba(34,211,238,0.4)',
        },
        border: 'rgba(139,92,246,0.2)',
        'border-bright': 'rgba(139,92,246,0.5)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        shimmer: 'shimmer 2s infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        float: 'float 6s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      boxShadow: {
        purple: '0 0 20px rgba(139,92,246,0.3)',
        cyan: '0 0 20px rgba(34,211,238,0.3)',
        card: '0 4px 24px rgba(0,0,0,0.4)',
      },
    },
  },
  plugins: [],
}

export default config
