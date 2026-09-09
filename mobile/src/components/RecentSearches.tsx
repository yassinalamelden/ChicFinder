/**
 * The strip of photos you searched recently.
 *
 * Tapping one runs the same search again, which is the common case: the first
 * shot rarely frames the outfit well, and getting back to it should not mean
 * opening the camera roll again.
 *
 * Entries hold a local URI, not a copy of the photo, so a thumbnail can fail to
 * load once the OS reclaims the cache or the user deletes the asset. That is a
 * normal outcome rather than an error: the entry removes itself quietly.
 */

import React from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";

import {
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../theme";
import type { RecentSearch } from "../lib/recentSearches";

interface RecentSearchesProps {
  items: RecentSearch[];
  onSelect: (uri: string) => void;
  /** Called when a thumbnail cannot be loaded, so the entry can be dropped. */
  onMissing: (uri: string) => void;
  onClear: () => void;
}

export function RecentSearches({
  items,
  onSelect,
  onMissing,
  onClear,
}: RecentSearchesProps) {
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);

  if (items.length === 0) return null;

  return (
    <View style={styles.wrap}>
      <View style={styles.headRow}>
        <Text style={styles.head}>Recent searches</Text>
        <Pressable
          onPress={onClear}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel="Clear recent searches"
        >
          <Text style={styles.clear}>Clear</Text>
        </Pressable>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
      >
        {items.map((item) => (
          <Pressable
            key={item.uri}
            onPress={() => onSelect(item.uri)}
            accessibilityRole="button"
            accessibilityLabel={`Search this photo again, ${item.count} ${
              item.count === 1 ? "match" : "matches"
            }`}
            style={({ pressed }) => [styles.tile, pressed && styles.tilePressed]}
          >
            <Image
              source={{ uri: item.uri }}
              style={styles.thumb}
              contentFit="cover"
              transition={120}
              onError={() => onMissing(item.uri)}
            />
            <View style={styles.badge}>
              <Ionicons name="refresh" size={11} color={colors.onAccent} />
              <Text style={styles.badgeText}>{item.count}</Text>
            </View>
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );
}

const makeStyles = (c: Palette) => ({
  wrap: { marginTop: spacing.xl, gap: spacing.sm },
  headRow: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    justifyContent: "space-between" as const,
  },
  head: { ...typography.label, color: c.faint },
  clear: {
    ...typography.label,
    color: c.muted,
  },

  row: { gap: spacing.sm + 2, paddingVertical: 2 },
  tile: {
    width: 78,
    height: 100,
    borderRadius: radius.md,
    overflow: "hidden" as const,
    backgroundColor: c.surfaceAlt,
    borderWidth: 1,
    borderColor: c.border,
  },
  tilePressed: { opacity: 0.85, transform: [{ scale: 0.97 }] },
  thumb: { width: "100%" as const, height: "100%" as const },

  // Sits over the photo, so it needs its own ground rather than the palette's.
  badge: {
    position: "absolute" as const,
    left: 6,
    bottom: 6,
    flexDirection: "row" as const,
    alignItems: "center" as const,
    gap: 3,
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: radius.pill,
    backgroundColor: c.accent,
  },
  badgeText: {
    ...typography.caption,
    fontSize: 11,
    lineHeight: 14,
    fontFamily: typography.bodyMedium.fontFamily,
    color: c.onAccent,
  },
});
