/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Core surfaces
        void: '#05070a', // page background, near-black
        panel: {
          DEFAULT: '#0d1117',
          light: '#10151d',
          border: 'rgba(148, 163, 184, 0.12)',
        },
        // Brand accents — used sparingly
        cyan: {
          accent: '#22d3ee',
          dim: '#0e7490',
          faint: 'rgba(34, 211, 238, 0.12)',
        },
        violet: {
          accent: '#a78bfa',
          dim: '#6d28d9',
          faint: 'rgba(167, 139, 250, 0.12)',
        },
        // Text
        ink: {
          primary: '#e6edf3',
          secondary: '#9aa7b8',
          muted: '#5b6676',
        },
        // Status palette — reserved, never reused for brand accents
        status: {
          info: '#38bdf8',
          caution: '#f5a524',
          warning: '#ef4444',
          good: '#34d399',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      backgroundImage: {
        'grid-faint':
          'linear-gradient(rgba(148,163,184,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.06) 1px, transparent 1px)',
      },
      backgroundSize: {
        grid: '32px 32px',
      },
      boxShadow: {
        glass: '0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px rgba(0,0,0,0.35)',
      },
    },
  },
  plugins: [],
}
