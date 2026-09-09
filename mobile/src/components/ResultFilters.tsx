/**
 * Sort and brand filtering for a grid of results.
 *
 * The brand chips are derived from the results themselves rather than from a
 * fixed list, so the control can never offer a brand that would return nothing,
 * and it disappears entirely when there is only one brand to choose from.
 */

import React, { useMemo } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import {
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../theme";
import type { ProductCardData } from "./ProductCard";

export type SortKey = "match" | "priceAsc" | "priceDesc";

const SORTS: Array<{ key: SortKey; label: string }> = [
  { key: "match", label: "Best match" },
  { key: "priceAsc", label: "Price low to high" },
  { key: "priceDesc", label: "Price high to low" },
];

export interface FilterState {
  sort: SortKey;
  /** null means every brand. */
  brand: string | null;
}

export const DEFAULT_FILTERS: FilterState = { sort: "match", brand: null };

/**
 * Applies a filter state to a list of cards.
 *
 * Items with no price sort last in both directions rather than being treated as
 * free or as infinitely expensive, either of which would put them somewhere
 * misleading.
 */
export function applyFilters(
  cards: ProductCardData[],
  filters: FilterState
): ProductCardData[] {
  const filtered = filters.brand
    ? cards.filter((card) => card.brand === filters.brand)
    : cards.slice();

  if (filters.sort === "match") return filtered;

  const priceOf = (card: ProductCardData) =>
    typeof card.priceEgp === "number" && card.priceEgp > 0 ? card.priceEgp : null;

  return filtered.sort((a, b) => {
    const pa = priceOf(a);
    const pb = priceOf(b);
    if (pa === null && pb === null) return 0;
    if (pa === null) return 1;
    if (pb === null) return -1;
    return filters.sort === "priceAsc" ? pa - pb : pb - pa;
  });
}

interface ResultFiltersProps {
  cards: ProductCardData[];
  value: FilterState;
  onChange: (next: FilterState) => void;
  /** Hides the sort-by-match option where there are no match scores. */
  hasMatchScores?: boolean;
}

export function ResultFilters({
  cards,
  value,
  onChange,
  hasMatchScores = true,
}: ResultFiltersProps) {
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);

  const brands = useMemo(() => {
    const found = new Set<string>();
    cards.forEach((card) => {
      if (card.brand) found.add(card.brand);
    });
    return Array.from(found).sort();
  }, [cards]);

  const sorts = hasMatchScores ? SORTS : SORTS.filter((s) => s.key !== "match");

  // Nothing to choose between, so the control would be decoration.
  if (cards.length < 2 || (brands.length < 2 && sorts.length < 2)) return null;

  const cycleSort = () => {
    Haptics.selectionAsync().catch(() => {});
    const i = sorts.findIndex((s) => s.key === value.sort);
    const next = sorts[(i + 1) % sorts.length];
    onChange({ ...value, sort: next.key });
  };

  const activeSort = sorts.find((s) => s.key === value.sort) ?? sorts[0];

  return (
    <View style={styles.wrap}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
      >
        {sorts.length > 1 ? (
          <Pressable
            onPress={cycleSort}
            accessibilityRole="button"
            accessibilityLabel={`Sort: ${activeSort.label}. Tap to change.`}
            style={({ pressed }) => [
              styles.chip,
              styles.sortChip,
              pressed && styles.chipPressed,
            ]}
          >
            <Ionicons name="swap-vertical" size={14} color={colors.text} />
            <Text style={styles.sortText}>{activeSort.label}</Text>
          </Pressable>
        ) : null}

        {brands.length > 1 ? (
          <>
            <Pressable
              onPress={() => onChange({ ...value, brand: null })}
              accessibilityRole="button"
              accessibilityState={{ selected: value.brand === null }}
              style={[styles.chip, value.brand === null && styles.chipActive]}
            >
              <Text
                style={[styles.chipText, value.brand === null && styles.chipTextActive]}
              >
                All brands
              </Text>
            </Pressable>

            {brands.map((brand) => {
              const active = value.brand === brand;
              return (
                <Pressable
                  key={brand}
                  onPress={() => {
                    Haptics.selectionAsync().catch(() => {});
                    onChange({ ...value, brand: active ? null : brand });
                  }}
                  accessibilityRole="button"
                  accessibilityState={{ selected: active }}
                  style={[styles.chip, active && styles.chipActive]}
                >
                  <Text style={[styles.chipText, active && styles.chipTextActive]}>
                    {brand}
                  </Text>
                </Pressable>
              );
            })}
          </>
        ) : null}
      </ScrollView>
    </View>
  );
}

const makeStyles = (c: Palette) => ({
  wrap: { marginTop: spacing.md },
  row: { gap: spacing.sm, paddingVertical: 2 },

  chip: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 9,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surface,
  },
  chipPressed: { opacity: 0.8 },
  chipActive: { backgroundColor: c.accent, borderColor: c.accent },
  chipText: {
    ...typography.caption,
    fontFamily: typography.bodyMedium.fontFamily,
    color: c.muted,
  },
  chipTextActive: { color: c.onAccent },

  // The sort control is a cycling button, not a selection, so it keeps the
  // neutral surface even while it carries a value.
  sortChip: { backgroundColor: c.surfaceAlt },
  sortText: {
    ...typography.caption,
    fontFamily: typography.bodyMedium.fontFamily,
    color: c.text,
  },
});
