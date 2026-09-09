/**
 * Product card used by search results, store catalogs and the saved list.
 *
 * Hierarchy, deliberately: the image carries the card, then the price, then the
 * name, then the brand as a small uppercase label. The earlier version gave all
 * three text lines near-equal weight and nothing led.
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
            <Ionicons name="shirt-outline" size={30} color={colors.faint} />
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
          style={[styles.saveButton, saved && styles.saveButtonActive]}
        >
          <Ionicons
            name={saved ? "heart" : "heart-outline"}
            size={18}
            color={colors.olive}
          />
        </Pressable>
      </Pressable>

      <View style={styles.body}>
        {item.brand ? (
          <Text style={styles.brand} numberOfLines={1}>
            {item.brand}
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
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
  },
  imageWrap: {
    position: "relative",
    aspectRatio: 3 / 4,
    backgroundColor: "#c9c0b2",
  },
  image: { width: "100%", height: "100%" },
  imageFallback: { alignItems: "center", justifyContent: "center" },

  matchBadge: {
    position: "absolute",
    top: 10,
    left: 10,
    backgroundColor: colors.accent,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  matchText: { ...typography.label, letterSpacing: 0.3, color: colors.olive },

  unavailableBadge: {
    position: "absolute",
    bottom: 10,
    left: 10,
    backgroundColor: colors.danger,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  unavailableText: { ...typography.label, color: colors.onOlive },

  saveButton: {
    position: "absolute",
    top: 10,
    right: 10,
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
    backgroundColor: "rgba(242, 239, 230, 0.92)",
  },
  saveButtonActive: { backgroundColor: colors.accent },

  body: { padding: spacing.md - 2, gap: 3 },
  brand: { ...typography.label, color: colors.faint },
  title: { ...typography.body, fontSize: 14, lineHeight: 19, color: colors.text },
  price: {
    ...typography.bodyMedium,
    fontFamily: typography.button.fontFamily,
    color: colors.text,
    marginTop: 4,
  },
  saveError: { ...typography.caption, color: colors.danger, marginTop: 2 },
});
