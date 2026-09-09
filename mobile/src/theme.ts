/**
 * Design tokens, carried over from the web frontend so the app and the site
 * read as one product. Kept in one file so a rebrand is a single edit.
 */

export const colors = {
  bg: "#0d0d0d",
  surface: "#161616",
  card: "#1c1c1c",
  border: "#2a2a2a",
  accent: "#e8ff47",
  accentHover: "#d4eb30",
  accent2: "#ff6b35",
  text: "#f0f0f0",
  muted: "#777777",
  danger: "#ff5a5a",
  unavailable: "#993333",
  overlay: "rgba(0,0,0,0.6)",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radius = {
  sm: 8,
  md: 14,
  lg: 20,
  pill: 999,
} as const;

export const typography = {
  display: { fontSize: 34, fontWeight: "700" as const, letterSpacing: -0.8 },
  title: { fontSize: 24, fontWeight: "700" as const, letterSpacing: -0.4 },
  heading: { fontSize: 18, fontWeight: "600" as const },
  body: { fontSize: 15, fontWeight: "400" as const },
  label: { fontSize: 13, fontWeight: "600" as const, letterSpacing: 0.4 },
  caption: { fontSize: 12, fontWeight: "400" as const },
} as const;

export const strings = {
  matchSuffix: "% Match",
  unavailable: "UNAVAILABLE",
  shopNow: "SHOP NOW",
  priceNa: "Price not available",
  notInEgypt: "Not in Egypt",
  emptyResultsTitle: "NO RESULTS",
  emptyResultsSubtitle: "Try a different photo",
} as const;
