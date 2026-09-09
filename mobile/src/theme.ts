/**
 * Design tokens for the ChicFinder app.
 *
 * These are the brand's real values, measured from the ChicFinder marketing
 * site rather than approximated, so the app and the site read as one product.
 * This is the only file that defines a colour, a size or a face: change it here
 * and the whole app follows.
 *
 * One rule the palette depends on: `lime` is a FILL, never text. Lime type on
 * the bone background fails contrast badly. Put lime behind something and set
 * that something in `olive`.
 */

export const colors = {
  /** Page ground. */
  bg: "#edeae2",
  /** Raised surfaces: cards, inputs, rows. */
  surface: "#f2efe6",
  /** Alias kept so existing imports of `card` keep working. */
  card: "#f2efe6",
  /** Hairline borders. Deliberately low contrast. */
  border: "rgba(51, 48, 48, 0.20)",
  /** Primary text and icons. */
  text: "#221e1c",
  /** Secondary text. */
  muted: "rgba(52, 49, 48, 0.62)",
  /** Tertiary text, placeholders, inactive icons. */
  faint: "rgba(52, 49, 48, 0.42)",
  /** Dark contrast blocks and the primary button. */
  olive: "#1e2300",
  /** The accent. Fills only, never text. */
  accent: "#dcff00",
  /** Soft accent wash for icon tiles and empty states. */
  accentSoft: "#eaf4a0",
  /** Destructive. Warmed so it belongs in this palette rather than iOS red. */
  danger: "#a63d2b",
  /** Text and icons that sit on `olive`. */
  onOlive: "#edeae2",
  onOliveMuted: "rgba(237, 234, 226, 0.62)",
  /** Scrim behind modals. */
  overlay: "rgba(30, 35, 0, 0.42)",
} as const;

export const fonts = {
  /** Anton. Uppercase only, by design: it has no lowercase character. */
  display: "Anton_400Regular",
  regular: "Geist_400Regular",
  medium: "Geist_500Medium",
  semibold: "Geist_600SemiBold",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 14,
  lg: 20,
  xl: 30,
  xxl: 46,
} as const;

export const radius = {
  sm: 12,
  md: 16,
  lg: 20,
  xl: 24,
  pill: 999,
} as const;

/**
 * Type ramp. Display styles set `textTransform: uppercase` because Anton has no
 * lowercase glyphs, so anything else renders as small caps at best.
 */
export const typography = {
  display: {
    fontFamily: fonts.display,
    fontSize: 38,
    lineHeight: 38,
    letterSpacing: -0.4,
    textTransform: "uppercase" as const,
  },
  displayLarge: {
    fontFamily: fonts.display,
    fontSize: 52,
    lineHeight: 48,
    letterSpacing: -0.8,
    textTransform: "uppercase" as const,
  },
  title: {
    fontFamily: fonts.display,
    fontSize: 26,
    lineHeight: 27,
    letterSpacing: -0.2,
    textTransform: "uppercase" as const,
  },
  heading: { fontFamily: fonts.semibold, fontSize: 17, lineHeight: 22 },
  body: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 23 },
  bodyMedium: { fontFamily: fonts.medium, fontSize: 15, lineHeight: 23 },
  button: { fontFamily: fonts.semibold, fontSize: 15 },
  caption: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 18 },
  /** Small uppercase label: brand names on cards, metadata, section labels. */
  label: {
    fontFamily: fonts.medium,
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: "uppercase" as const,
  },
} as const;

export const strings = {
  matchSuffix: "% MATCH",
  unavailable: "UNAVAILABLE",
  priceNa: "Price not available",
  emptyResultsTitle: "No results",
  emptyResultsSubtitle: "Try a different photo",
} as const;
