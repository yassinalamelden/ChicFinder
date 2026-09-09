/**
 * Product card used by search results, store catalogs and the saved list.
 *
 * The three screens hand it slightly different shapes, so it takes a small
 * normalised prop set rather than any one API type.
 */

import React, { useState } from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { colors, radius, spacing, strings, typography } from "../theme";
import { useSaved } from "../context/SavedContext";

export interface ProductCardData {
  id: string;
  title?: string | null;
  brand?: string | null;
  priceEgp?: number | null;
  imageUrl?: string | null;
  productUrl?: string | null;
  /** 0 to 1. Shown as a match badge on search results only. */
  matchScore?: number | null;
  available?: boolean;
}

const EGP = new Intl.NumberFormat("en-EG", {
  style: "currency",
  currency: "EGP",
  maximumFractionDigits: 0,
});

export function ProductCard({ item }: { item: ProductCardData }) {
  const { isSaved, toggleSaved } = useSaved();
  const [saveError, setSaveError] = useState(false);
  const saved = isSaved(item.id);
  const available = item.available ?? true;

  const priceLabel =
    typeof item.priceEgp === "number" && item.priceEgp > 0
      ? EGP.format(item.priceEgp)
      : strings.priceNa;

  const handleSave = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    setSaveError(false);
    try {
      await toggleSaved(item.id);
    } catch {
      setSaveError(true);
    }
  };

  const openProduct = () => {
    if (item.productUrl) Linking.openURL(item.productUrl).catch(() => {});
  };

  return (
    <View style={styles.card}>
      <Pressable
        onPress={openProduct}
        disabled={!item.productUrl}
        accessibilityRole={item.productUrl ? "link" : "image"}
        accessibilityLabel={`${item.title ?? "Fashion item"}${
          item.brand ? ` by ${item.brand}` : ""
        }, ${priceLabel}`}
        style={styles.imageWrap}
      >
        {item.imageUrl ? (
          <Image
            source={{ uri: item.imageUrl }}
            style={styles.image}
            contentFit="cover"
            transition={180}
            recyclingKey={item.id}
          />
        ) : (
          <View style={[styles.image, styles.imageFallback]}>
            <Ionicons name="shirt-outline" size={32} color={colors.muted} />
          </View>
        )}

        {typeof item.matchScore === "number" ? (
          <View style={styles.matchBadge}>
            <Text style={styles.matchText}>
              {Math.round(item.matchScore * 100)}
              {strings.matchSuffix}
            </Text>
          </View>
        ) : null}

        {!available ? (
          <View style={styles.unavailableBadge}>
            <Text style={styles.unavailableText}>{strings.unavailable}</Text>
          </View>
        ) : null}

        <Pressable
          onPress={handleSave}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel={saved ? "Remove from saved" : "Save item"}
          accessibilityState={{ selected: saved }}
          style={styles.saveButton}
        >
          <Ionicons
            name={saved ? "heart" : "heart-outline"}
            size={20}
            color={saved ? colors.accent2 : colors.text}
          />
        </Pressable>
      </Pressable>

      <View style={styles.body}>
        {item.brand ? (
          <Text style={styles.brand} numberOfLines={1}>
            {item.brand.toUpperCase()}
          </Text>
        ) : null}
        <Text style={styles.title} numberOfLines={2}>
          {item.title ?? "Fashion item"}
        </Text>
        <Text style={styles.price}>{priceLabel}</Text>
        {saveError ? (
          <Text style={styles.saveError}>Could not update. Tap again.</Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
  },
  imageWrap: { position: "relative", aspectRatio: 3 / 4, backgroundColor: colors.surface },
  image: { width: "100%", height: "100%" },
  imageFallback: { alignItems: "center", justifyContent: "center" },

  matchBadge: {
    position: "absolute",
    top: spacing.sm,
    left: spacing.sm,
    backgroundColor: colors.accent,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radius.pill,
  },
  matchText: { ...typography.caption, fontWeight: "700", color: "#0d0d0d" },

  unavailableBadge: {
    position: "absolute",
    bottom: spacing.sm,
    left: spacing.sm,
    backgroundColor: colors.unavailable,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radius.sm,
  },
  unavailableText: { ...typography.caption, fontWeight: "700", color: colors.text },

  saveButton: {
    position: "absolute",
    top: spacing.sm,
    right: spacing.sm,
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
    backgroundColor: colors.overlay,
  },

  body: { padding: spacing.sm, gap: 2 },
  brand: { ...typography.caption, color: colors.muted, letterSpacing: 0.6 },
  title: { ...typography.body, color: colors.text, fontWeight: "500" },
  price: { ...typography.body, color: colors.accent, fontWeight: "700", marginTop: 2 },
  saveError: { ...typography.caption, color: colors.danger, marginTop: 2 },
});
