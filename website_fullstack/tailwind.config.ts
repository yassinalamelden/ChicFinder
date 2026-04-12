import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "cf-bg": "#0d0d0d",
        "cf-surface": "#161616",
        "cf-card": "#1c1c1c",
        "cf-border": "#2a2a2a",
        "cf-accent": "#e8ff47",
        "cf-accent2": "#ff6b35",
        "cf-text": "#f0f0f0",
        "cf-muted": "#777777",
      },
      fontFamily: {
        display: ["var(--font-bebas)", "sans-serif"],
        body: ["var(--font-dm-sans)", "sans-serif"],
      },
    },
  },
};

export default config;
