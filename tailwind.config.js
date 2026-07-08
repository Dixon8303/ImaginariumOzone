export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display:          ['"Bebas Neue"', '"Impact"', 'sans-serif'],
        'display-heavy':  ['"Anton"', '"Impact"', 'sans-serif'],
        serif:            ['"EB Garamond"', '"Cormorant Garamond"', 'Georgia', 'serif'],
        'serif-display':  ['"Cormorant Garamond"', '"EB Garamond"', 'Georgia', 'serif'],
        ui:               ['"Jost"', '-apple-system', 'sans-serif'],
        mono:             ['"IBM Plex Mono"', '"Menlo"', 'monospace'],
      },
      colors: {
        'bg-black':    '#0B0906',
        'bg-deep':     '#110D08',
        'bg-warm':     '#161109',
        'bg-code':     '#0E0A05',
        'ink-paper':   '#F4ECD8',
        'ink-cream':   '#E8DFC6',
        'ink-muted':   '#B3A684',
        'ink-ghost':   '#7A6F54',
        'gold':        '#D4B26A',
        'gold-bright': '#E8C97C',
        'gold-deep':   '#9B7838',
        'gold-blood':  '#6B4E1E',
        'crimson':     '#8B2E26',
        'ember':       '#B85A2E',
        'sage':        '#4A6B3A',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
