/**
 * Product card used by search results, store catalogs and the saved list.
 *
 * Hierarchy: the image carries the card, then the price, then the name, then
 * the brand as a small uppercase label.
 */

import React, { useState } from "react";
import { Linking, Pressable, Text, View } from "react-native";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import {
  elevation,
  radius,
  spacing,
  strings,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../theme";
import { useRouter } from "expo-router";

import { SignInRequiredError, useSaved } from "../context/SavedContext";

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
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const router = useRouter();
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
    } catch (err) {
      if (err instanceof SignInRequiredError) {
        router.push("/(auth)/welcome");
        return;
      }
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
        style={({ pressed }) => [styles.imageWrap, pressed && styles.pressed]}
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
            <Ionicons name="shirt-outline" size={28} color={colors.faint} />
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
            color={saved ? colors.onAccent : colors.text}
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

const makeStyles = (c: Palette) => ({
  card: {
    flex: 1,
    backgroundColor: c.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: c.border,
    overflow: "hidden" as const,
    ...elevation(c, 1),
  },
  pressed: { opacity: 0.9 },
  imageWrap: {
    position: "relative" as const,
    aspectRatio: 3 / 4,
    backgroundColor: c.surfaceAlt,
  },
  image: { width: "100%" as const, height: "100%" as const },
  imageFallback: { alignItems: "center" as const, justifyContent: "center" as const },

  matchBadge: {
    position: "absolute" as const,
    top: 10,
    left: 10,
    backgroundColor: c.accent,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  matchText: { ...typography.label, letterSpacing: 0.3, color: c.onAccent },

  unavailableBadge: {
    position: "absolute" as const,
    bottom: 10,
    left: 10,
    backgroundColor: c.danger,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  unavailableText: { ...typography.label, color: "#ffffff" },

  saveButton: {
    position: "absolute" as const,
    top: 10,
    right: 10,
    width: 34,
    height: 34,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    borderRadius: radius.pill,
    backgroundColor: c.glass,
    borderWidth: 1,
    borderColor: c.glassBorder,
  },
  saveButtonActive: { backgroundColor: c.accent, borderColor: c.accent },

  body: { padding: spacing.md - 2, gap: 3 },
  brand: { ...typography.label, color: c.faint },
  title: { ...typography.body, fontSize: 14, lineHeight: 19, color: c.text },
  price: {
    ...typography.bodyMedium,
    fontFamily: typography.button.fontFamily,
    color: c.text,
    marginTop: 4,
  },
  saveError: { ...typography.caption, color: c.danger, marginTop: 2 },
});
