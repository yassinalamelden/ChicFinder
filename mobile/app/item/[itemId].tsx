/**
 * One item, full screen.
 *
 * Before this, tapping a match handed the user straight to the brand's website.
 * That loses everything the app knows about the item, and it makes the app feel
 * like a directory of links rather than a place. The browser is still where a
 * purchase happens, but it is now a deliberate step at the end rather than the
 * response to every tap.
 *
 * The screen paints from whatever the card already knew before the fetch lands,
 * so opening it never shows an empty frame.
 */

import React, { useCallback, useEffect, useState } from "react";
import { Linking, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { Button, LoadingState, MessageState } from "../../src/components/ui";
import { SignInRequiredError, useSaved } from "../../src/context/SavedContext";
import { getItem, resolveImageUrl } from "../../src/lib/api";
import {
  elevation,
  radius,
  spacing,
  strings,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../../src/theme";
import type { StoreItem } from "../../src/types/api";

const EGP = new Intl.NumberFormat("en-EG", {
  style: "currency",
  currency: "EGP",
  maximumFractionDigits: 0,
});

/** Params a card can hand over so the screen has something to draw immediately. */
interface ItemParams {
  itemId: string;
  title?: string;
  brand?: string;
  price?: string;
  image?: string;
  productUrl?: string;
}

export default function ItemDetailScreen() {
  // Typed through a cast rather than the generic: expo-router's typed-routes
  // build constrains that generic to the route's own path params, so the extra
  // paint-ahead values would not be expressible there.
  const params = useLocalSearchParams() as Partial<ItemParams>;
  const itemId = params.itemId ?? "";
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const { isSaved, toggleSaved } = useSaved();

  const [item, setItem] = useState<StoreItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState(false);

  const load = useCallback(async () => {
    if (!itemId) return;
    setError(null);
    try {
      setItem(await getItem(itemId));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [itemId]);

  useEffect(() => {
    load();
  }, [load]);

  // Everything below reads through these, so the passed-in values cover the gap
  // until the fetch lands and the fetched values win once it does.
  const title = item?.name ?? params.title ?? "Fashion item";
  const brand = item?.brand ?? params.brand;
  const imageUrl = resolveImageUrl(item?.image_url) ?? params.image;
  const productUrl = item?.product_url ?? params.productUrl;
  const priceEgp =
    typeof item?.price_egp === "number"
      ? item.price_egp
      : params.price
        ? Number(params.price)
        : undefined;

  const priceLabel =
    typeof priceEgp === "number" && !Number.isNaN(priceEgp) && priceEgp > 0
      ? EGP.format(priceEgp)
      : strings.priceNa;

  const saved = isSaved(itemId);

  const onSave = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    setSaveError(false);
    try {
      await toggleSaved(itemId);
    } catch (err) {
      if (err instanceof SignInRequiredError) {
        router.push("/(auth)/welcome");
        return;
      }
      setSaveError(true);
    }
  };

  // Only a total miss is an error state. If the card gave us a title, a failed
  // fetch still leaves a usable screen, so it is not worth blanking.
  if (loading && !params.title) return <LoadingState label="Loading item" />;

  if (error && !item && !params.title) {
    return (
      <MessageState
        icon="cloud-offline-outline"
        tone="error"
        title="Could not load this item"
        subtitle={error}
        action={<Button label="Retry" onPress={load} arrow />}
      />
    );
  }

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + 120 },
        ]}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.imageWrap}>
          {imageUrl ? (
            <Image
              source={{ uri: imageUrl }}
              style={styles.image}
              contentFit="cover"
              transition={200}
            />
          ) : (
            <View style={[styles.image, styles.imageFallback]}>
              <Ionicons name="shirt-outline" size={44} color={colors.faint} />
            </View>
          )}

          <Pressable
            onPress={onSave}
            hitSlop={10}
            accessibilityRole="button"
            accessibilityLabel={saved ? "Remove from saved" : "Save item"}
            accessibilityState={{ selected: saved }}
            style={[styles.saveButton, saved && styles.saveButtonActive]}
          >
            <Ionicons
              name={saved ? "heart" : "heart-outline"}
              size={21}
              color={saved ? colors.onAccent : "#edeae2"}
            />
          </Pressable>
        </View>

        <View style={styles.body}>
          {brand ? <Text style={styles.brand}>{brand}</Text> : null}
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.price}>{priceLabel}</Text>

          {item?.sizes?.length ? (
            <View style={styles.block}>
              <Text style={styles.blockLabel}>Sizes</Text>
              <View style={styles.sizes}>
                {item.sizes.map((size) => (
                  <View key={size} style={styles.size}>
                    <Text style={styles.sizeText}>{size}</Text>
                  </View>
                ))}
              </View>
            </View>
          ) : null}

          {item?.description ? (
            <View style={styles.block}>
              <Text style={styles.blockLabel}>Details</Text>
              <Text style={styles.description}>{item.description}</Text>
            </View>
          ) : null}

          {item ? (
            <View style={styles.facts}>
              {([
                ["Category", item.category],
                ["Colour", item.color],
                ["Store", item.store_location],
              ] as Array<[string, string | undefined]>)
                .filter(([, value]) => Boolean(value))
                .map(([label, value]) => (
                  <View key={label} style={styles.factRow}>
                    <Text style={styles.factLabel}>{label}</Text>
                    <Text style={styles.factValue}>{value}</Text>
                  </View>
                ))}
            </View>
          ) : null}

          {item?.store_id ? (
            <Pressable
              onPress={() => router.push(`/store/${item.store_id}`)}
              accessibilityRole="button"
              accessibilityLabel={`See more from ${brand ?? "this brand"}`}
              style={({ pressed }) => [styles.storeRow, pressed && styles.pressed]}
            >
              <Ionicons name="storefront-outline" size={18} color={colors.muted} />
              <Text style={styles.storeText}>
                More from {brand ?? "this brand"}
              </Text>
              <Ionicons name="chevron-forward" size={17} color={colors.faint} />
            </Pressable>
          ) : null}

          {saveError ? (
            <Text style={styles.saveErrorText}>
              Could not update your saved items. Try again.
            </Text>
          ) : null}
        </View>
      </ScrollView>

      {/* Pinned, because buying is the one thing this screen exists to enable. */}
      <View style={[styles.bar, { paddingBottom: insets.bottom + spacing.sm }]}>
        <Button
          label={saved ? "Saved" : "Save"}
          variant="secondary"
          icon={saved ? "heart" : "heart-outline"}
          onPress={onSave}
          style={styles.barSave}
        />
        <Button
          label="Visit store"
          variant="accent"
          arrow
          disabled={!productUrl}
          hint="Opens the brand's website in your browser"
          onPress={() => {
            if (productUrl) Linking.openURL(productUrl).catch(() => {});
          }}
          style={styles.barBuy}
        />
      </View>
    </View>
  );
}

const makeStyles = (c: Palette) => ({
  root: { flex: 1, backgroundColor: c.bg },
  content: { paddingBottom: spacing.xxl },

  imageWrap: {
    width: "100%" as const,
    aspectRatio: 3 / 4,
    backgroundColor: c.surfaceAlt,
  },
  image: { width: "100%" as const, height: "100%" as const },
  imageFallback: { alignItems: "center" as const, justifyContent: "center" as const },
  saveButton: {
    position: "absolute" as const,
    top: spacing.md,
    right: spacing.md,
    width: 44,
    height: 44,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    borderRadius: radius.pill,
    backgroundColor: "rgba(20, 21, 15, 0.55)",
    borderWidth: 1,
    borderColor: "rgba(237, 234, 226, 0.35)",
  },
  saveButtonActive: { backgroundColor: c.accent, borderColor: c.accent },

  body: { padding: spacing.lg, gap: spacing.xs },
  brand: { ...typography.label, color: c.faint },
  title: { ...typography.title, color: c.text },
  price: {
    ...typography.heading,
    fontSize: 22,
    lineHeight: 28,
    color: c.text,
    marginTop: spacing.xs,
  },

  block: { marginTop: spacing.lg, gap: spacing.sm },
  blockLabel: { ...typography.label, color: c.faint },
  description: { ...typography.body, color: c.muted },

  sizes: { flexDirection: "row" as const, flexWrap: "wrap" as const, gap: spacing.sm },
  size: {
    minWidth: 48,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surface,
    alignItems: "center" as const,
  },
  sizeText: { ...typography.bodyMedium, fontSize: 14, color: c.text },

  facts: {
    marginTop: spacing.lg,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surface,
    overflow: "hidden" as const,
  },
  factRow: {
    flexDirection: "row" as const,
    justifyContent: "space-between" as const,
    alignItems: "center" as const,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md - 2,
  },
  factLabel: { ...typography.caption, color: c.muted },
  factValue: { ...typography.bodyMedium, fontSize: 14, color: c.text },

  storeRow: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    gap: spacing.sm,
    marginTop: spacing.lg,
    padding: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surface,
    ...elevation(c, 1),
  },
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  storeText: { ...typography.bodyMedium, fontSize: 14, color: c.text, flex: 1 },

  saveErrorText: { ...typography.caption, color: c.danger, marginTop: spacing.md },

  bar: {
    position: "absolute" as const,
    left: 0,
    right: 0,
    bottom: 0,
    flexDirection: "row" as const,
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm + 2,
    backgroundColor: c.bg,
    borderTopWidth: 1,
    borderTopColor: c.border,
  },
  barSave: { flex: 0, paddingHorizontal: spacing.lg },
  barBuy: { flex: 1 },
});
