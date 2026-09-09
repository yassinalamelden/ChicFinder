/**
 * Design tokens for the ChicFinder app.
 *
 * Two palettes, one set of names. Screens never import a colour directly: they
 * call `useThemedStyles(makeStyles)` and receive whichever palette matches the
 * phone's appearance setting, so light and dark stay in step by construction.
 *
 * Colour roles, so the dark palette inverts correctly instead of guessing:
 *   bg        the page ground
 *   surface   raised cards, inputs, rows
 *   contrast  the heavy block: primary button, stat tile, search dropzone
 *   accent    amber. A FILL, never text: it fails contrast on both grounds
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { StyleSheet, useColorScheme } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

export interface Palette {
  bg: string;
  surface: string;
  surfaceAlt: string;
  border: string;
  text: string;
  muted: string;
  faint: string;
  contrast: string;
  onContrast: string;
  onContrastMuted: string;
  accent: string;
  accentSoft: string;
  onAccent: string;
  danger: string;
  dangerSoft: string;
  overlay: string;
  /** Tint for the blurred tab bar, which sits over scrolling content. */
  glass: string;
  glassBorder: string;
  /** expo-blur needs to know which way to blur. */
  blurTint: "light" | "dark";
  shadow: string;
}

const light: Palette = {
  bg: "#edeae2",
  surface: "#f6f4ee",
  surfaceAlt: "#e5e1d7",
  border: "rgba(51, 48, 48, 0.16)",
  text: "#221e1c",
  muted: "rgba(52, 49, 48, 0.64)",
  faint: "rgba(52, 49, 48, 0.42)",
  contrast: "#1e2300",
  onContrast: "#edeae2",
  onContrastMuted: "rgba(237, 234, 226, 0.62)",
  accent: "#e9a03c",
  accentSoft: "#f4e2c4",
  onAccent: "#1e2300",
  danger: "#a63d2b",
  dangerSoft: "rgba(166, 61, 43, 0.12)",
  overlay: "rgba(30, 35, 0, 0.42)",
  glass: "rgba(237, 234, 226, 0.72)",
  glassBorder: "rgba(51, 48, 48, 0.14)",
  blurTint: "light",
  shadow: "#2a2618",
};

/**
 * Dark is warm, not neutral grey: the ground keeps an olive cast so the amber
 * still belongs to it. `contrast` inverts to bone, which makes the primary
 * button light-on-dark exactly as it is dark-on-light in the other palette.
 */
const dark: Palette = {
  bg: "#14150f",
  surface: "#1e2017",
  surfaceAlt: "#282b1f",
  border: "rgba(237, 234, 226, 0.14)",
  text: "#edeae2",
  muted: "rgba(237, 234, 226, 0.64)",
  faint: "rgba(237, 234, 226, 0.40)",
  contrast: "#edeae2",
  onContrast: "#14150f",
  onContrastMuted: "rgba(20, 21, 15, 0.62)",
  accent: "#e9a03c",
  accentSoft: "rgba(233, 160, 60, 0.20)",
  onAccent: "#14150f",
  danger: "#e0785c",
  dangerSoft: "rgba(224, 120, 92, 0.16)",
  overlay: "rgba(0, 0, 0, 0.55)",
  glass: "rgba(20, 21, 15, 0.68)",
  glassBorder: "rgba(237, 234, 226, 0.12)",
  blurTint: "dark",
  shadow: "#000000",
};

export const palettes = { light, dark };

/** What the user picked in Profile, not what the phone is currently showing. */
export type ThemeMode = "system" | "light" | "dark";

interface ThemeContextValue {
  colors: Palette;
  mode: ThemeMode;
  /** The palette actually in use, once "system" has been resolved. */
  resolved: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

const MODE_KEY = "chicfinder.themeMode";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const system = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>("system");

  // Restore the saved choice. Until it lands the app follows the system, which
  // is the right default and avoids a flash of the wrong palette.
  useEffect(() => {
    AsyncStorage.getItem(MODE_KEY)
      .then((saved) => {
        if (saved === "light" || saved === "dark" || saved === "system") {
          setModeState(saved);
        }
      })
      .catch(() => {});
  }, []);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    AsyncStorage.setItem(MODE_KEY, next).catch(() => {});
  }, []);

  const resolved: "light" | "dark" =
    mode === "system" ? (system === "dark" ? "dark" : "light") : mode;

  const value = useMemo<ThemeContextValue>(
    () => ({ colors: palettes[resolved], mode, resolved, setMode }),
    [resolved, mode, setMode]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Palette {
  const ctx = useContext(ThemeContext);
  // Falling back keeps any component usable outside the provider (tests, a
  // screen rendered before the tree mounts) rather than throwing.
  return ctx?.colors ?? light;
}

/** For the appearance control in Profile. */
export function useThemeMode(): {
  mode: ThemeMode;
  resolved: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
} {
  const ctx = useContext(ThemeContext);
  if (!ctx) return { mode: "system", resolved: "light", setMode: () => {} };
  return { mode: ctx.mode, resolved: ctx.resolved, setMode: ctx.setMode };
}

/**
 * Builds a StyleSheet from the active palette and rebuilds it when the phone
 * switches appearance. Screens use this instead of a module-level
 * StyleSheet.create, which would freeze one palette in place.
 */
export function useThemedStyles<T extends StyleSheet.NamedStyles<T>>(
  factory: (c: Palette) => T
): T {
  const colors = useTheme();
  return useMemo(() => StyleSheet.create(factory(colors)), [colors, factory]);
}

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
  lg: 22,
  xl: 28,
  pill: 999,
} as const;

/** Height of the floating glass tab bar, so screens can pad clear of it. */
export const TAB_BAR_HEIGHT = 72;

/**
 * Type ramp.
 *
 * Anton's cap height nearly fills its em box, and React Native clips a glyph to
 * its line box on iOS. A lineHeight near the fontSize therefore shaves the top
 * off every capital, which is what cropped these headings twice. Display styles
 * lead at ~1.25x and carry a little top padding, which costs nothing and is the
 * only thing that reliably keeps Anton intact.
 */
export const typography = {
  display: {
    fontFamily: fonts.display,
    fontSize: 34,
    lineHeight: 44,
    letterSpacing: -0.2,
    textTransform: "uppercase" as const,
    paddingTop: 4,
  },
  displayLarge: {
    fontFamily: fonts.display,
    fontSize: 44,
    lineHeight: 56,
    letterSpacing: -0.6,
    textTransform: "uppercase" as const,
    paddingTop: 4,
  },
  title: {
    fontFamily: fonts.display,
    fontSize: 24,
    lineHeight: 32,
    letterSpacing: -0.1,
    textTransform: "uppercase" as const,
    paddingTop: 2,
  },
  heading: { fontFamily: fonts.semibold, fontSize: 17, lineHeight: 23 },
  body: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 22 },
  bodyMedium: { fontFamily: fonts.medium, fontSize: 15, lineHeight: 22 },
  button: { fontFamily: fonts.semibold, fontSize: 16 },
  caption: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 18 },
  label: {
    fontFamily: fonts.medium,
    fontSize: 11,
    letterSpacing: 1.1,
    textTransform: "uppercase" as const,
  },
} as const;

/** Soft elevation for cards. Kept subtle: this palette is matte, not glossy. */
export const elevation = (c: Palette, level: 1 | 2 = 1) => ({
  shadowColor: c.shadow,
  shadowOpacity: level === 1 ? 0.06 : 0.1,
  shadowRadius: level === 1 ? 10 : 20,
  shadowOffset: { width: 0, height: level === 1 ? 3 : 8 },
  elevation: level === 1 ? 2 : 6,
});

export const strings = {
  matchSuffix: "% MATCH",
  unavailable: "UNAVAILABLE",
  priceNa: "Price not available",
  emptyResultsTitle: "No results",
  emptyResultsSubtitle: "Try a different photo",
} as const;
