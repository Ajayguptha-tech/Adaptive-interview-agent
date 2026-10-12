import colors from 'tailwindcss/colors.js'

/**
 * Design tokens — "lime / charcoal / off-white" redesign.
 *
 * The original UI was authored against a dark theme using Tailwind's slate /
 * cyan / violet scales. To restyle every existing screen without touching its
 * logic, those scale names are re-pointed here to the new palette and FLIPPED
 * (50 <-> 950) so that "light text on dark" classes become "dark text on light".
 */
const STEPS = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950']
const flip = (scale) => {
  const out = {}
  STEPS.forEach((k, i) => { out[k] = scale[STEPS[STEPS.length - 1 - i]] })
  return out
}

// Warm neutral (off-white -> charcoal)
const warm = {
  50: '#f7f6f1', 100: '#efeee8', 200: '#e2e1d9', 300: '#c9c8bf', 400: '#a3a299',
  500: '#7d7c74', 600: '#5e5d56', 700: '#44443d', 800: '#2b2c26', 900: '#1b1c17', 950: '#111210',
}
// Signature lime
const lime = {
  50: '#f6fddc', 100: '#ecfbb4', 200: '#e0f882', 300: '#d2f34f', 400: '#c6ee2e',
  500: '#b4e01a', 600: '#8fb80f', 700: '#6c8c0e', 800: '#51690f', 900: '#41550f', 950: '#1f2c04',
}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        slate: flip(warm),
        cyan: flip(lime),
        sky: flip(lime),
        blue: flip(lime),
        violet: flip(colors.neutral),
        indigo: flip(colors.neutral),
        emerald: flip(colors.emerald),
        amber: flip(colors.amber),
        rose: flip(colors.rose),
        lime,
        ink: warm[950],
        charcoal: warm[900],
        paper: '#f4f3ee',
        orbit: {
          bg: '#f4f3ee', surface: '#ffffff', card: '#ffffff',
          border: 'rgba(17,18,16,0.10)', cyan: '#c6ee2e', electric: '#b4e01a',
          violet: '#44443d', indigo: '#2b2c26', mint: '#10b981', amber: '#f59e0b', rose: '#f43f5e',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
      },
      borderRadius: { '4xl': '2rem' },
      boxShadow: {
        'glow-cyan': '0 6px 20px -8px rgba(143,184,15,0.55)',
        'glow-violet': '0 6px 20px -8px rgba(17,18,16,0.35)',
        'glow-mint': '0 6px 20px -8px rgba(16,185,129,0.4)',
        'glow-rose': '0 6px 20px -8px rgba(244,63,94,0.4)',
        glass: '0 1px 2px rgba(17,18,16,0.04), 0 8px 24px -12px rgba(17,18,16,0.12)',
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 20s linear infinite',
        float: 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: { '0%, 100%': { transform: 'translateY(0px)' }, '50%': { transform: 'translateY(-8px)' } },
      },
    },
  },
  plugins: [],
}
