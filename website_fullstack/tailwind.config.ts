import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "cf-bg": "#121210",
        "cf-surface": "#1d1c19",
        "cf-card": "#242320",
        "cf-border": "#333230",
        "cf-accent": "#f5c842",
        "cf-accent2": "#e05a3a",
        "cf-text": "#f2ede8",
        "cf-muted": "#847f79",
      },
      fontFamily: {
        display: ["var(--font-instrument-serif)", "serif"],
        body: ["var(--font-dm-sans)", "sans-serif"],
      },
    },
  },
};

export default config;
