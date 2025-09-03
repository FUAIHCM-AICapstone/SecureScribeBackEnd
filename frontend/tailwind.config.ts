import type { Config } from 'tailwindcss';

export default {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        foreground: 'var(--foreground)',
        primary: {
          100: 'rgb(219 234 254 )',
          900: 'rgb(30 58 138)',
        },
      },
      fontFamily: {
        display: ['Sofia', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config;
