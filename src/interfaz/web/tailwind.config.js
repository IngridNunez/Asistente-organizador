/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sara: {
          fondo: '#E6F7F0',
          acento: '#F28CB1',
          'acento-hover': '#e07299',
          superficie: '#FFFDFB',
          texto: '#2B2B38',
          'texto-suave': '#5e6278',
        },
      },
      keyframes: {
        'pulse-listening': {
          '0%, 100%': {
            boxShadow:
              '0 0 0 0 rgba(242, 140, 177, .7), 0 0 0 0 rgba(77, 208, 162, .45)',
          },
          '50%': {
            boxShadow:
              '0 0 0 20px rgba(242, 140, 177, 0), 0 0 0 36px rgba(77, 208, 162, 0)',
          },
        },
        'pulse-speaking': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(56, 189, 248, .65)' },
          '50%': { boxShadow: '0 0 0 22px rgba(56, 189, 248, 0)' },
        },
      },
      animation: {
        'pulse-listening': 'pulse-listening 1.8s infinite',
        'pulse-speaking': 'pulse-speaking 1.5s infinite',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
