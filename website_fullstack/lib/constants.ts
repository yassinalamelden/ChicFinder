/**
 * Shared constants for ProductCard and ResultsGallery components
 */

export const PRODUCT_CARD = {
  IMAGE_PLACEHOLDER_EMOJI: "👗",
  MATCH_SUFFIX: "% Match",
  UNAVAILABLE_TEXT: "UNAVAILABLE",
  SHOP_NOW_TEXT: "SHOP NOW",
  PRICE_NA: "Price not available",
  NOT_IN_EGYPT: "Not in Egypt",
} as const;

export const RESULTS_GALLERY = {
  EMPTY_STATE_TITLE: "NO RESULTS",
  EMPTY_STATE_SUBTITLE: "Try a different image",
  RESULTS_LABEL: "results",
  MS_SUFFIX: "ms",
  SKELETON_COUNT_DEFAULT: 4,
} as const;

export const THEME = {
  COLORS: {
    BG: "#0d0d0d",
    SURFACE: "#161616",
    CARD: "#1c1c1c",
    BORDER: "#2a2a2a",
    ACCENT: "#e8ff47",
    ACCENT2: "#ff6b35",
    TEXT: "#f0f0f0",
    MUTED: "#777777",
    UNAVAILABLE_BG: "#993333", // red-dark for unavailable items
    ACCENT_HOVER: "#d4eb30",
  },
} as const;
