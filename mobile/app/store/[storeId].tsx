/**
 * Store detail: brand header plus its catalog, filterable by category.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { FlatList, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useLocalSearchParams, useNavigation } from "expo-router";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";

import { Button, LoadingState, MessageState } from "../../src/components/ui";
import { ProductCard, type ProductCardData } from "../../src/components/ProductCard";
import { getStoreDetail, resolveImageUrl } from "../../src/lib/api";
import {
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../../src/theme";
import type { Store, StoreItem } from "../../src/types/api";

const ALL = "All";

/** Categories arrive lowercase from the catalog; chips read better cased. */
function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function StoreDetailScreen() {
  const { storeId } = useLocalSearchParams<{ storeId: string }>();
  const navigation = useNavigation();
  const insets = useSafeAreaInsets();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);

  const [store, setStore] = useState<Store | null>(null);
  const [items, setItems] = useState<StoreItem[]>([]);
  const [category, setCategory] = useState(ALL);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!storeId) return;
    setError(null);
    try {
      const data = await getStoreDetail(storeId);
      setStore(data.store);
      setItems(data.items);
      navigation.setOptions({ title: data.store.name });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [storeId, navigation]);

  useEffect(() => {
    load();
  }, [load]);

  const categories = useMemo(() => {
    const found = new Set(items.map((i) => i.category).filter(Boolean) as string[]);
    return [ALL, ...Array.from(found).sort()];
  }, [items]);

  const visible = useMemo(
    () => (category === ALL ? items : items.filter((i) => i.category === category)),
    [items, category]
  );

  const cards: ProductCardData[] = visible.map((item) => ({
    id: item.id,
    title: item.name,
    brand: item.brand,
    priceEgp: item.price_egp,
    imageUrl: resolveImageUrl(item.image_url),
    productUrl: item.product_url,
  }));

  if (loading) return <LoadingState label="Loading store" />;

  if (error || !store) {
    return (
      <MessageState
        icon="cloud-offline-outline"
        tone="error"
        title="Could not load this store"
        subtitle={error ?? undefined}
        action={<Button label="Retry" onPress={load} arrow />}
      />
    );
  }

  return (
    <FlatList
      style={styles.root}
      data={cards}
      keyExtractor={(item) => item.id}
      numColumns={2}
      columnWrapperStyle={cards.length ? styles.column : undefined}
      contentContainerStyle={[
        styles.content,
        { paddingBottom: insets.bottom + spacing.xxl },
      ]}
      showsVerticalScrollIndicator={false}
      renderItem={({ item }) => <ProductCard item={item} />}
      ListHeaderComponent={
        <View style={styles.header}>
          <View style={styles.brandRow}>
            <View style={styles.logoWrap}>
              {store.logo_url ? (
                <Image source={{ uri: store.logo_url }} style={styles.logo} contentFit="cover" />
              ) : (
                <Ionicons name="storefront-outline" size={28} color={colors.onAccent} />
              )}
            </View>
            <View style={styles.brandBody}>
              <Text style={styles.name}>{store.name}</Text>
              {store.location ? (
                <View style={styles.locationRow}>
                  <Ionicons name="location-outline" size={12} color={colors.faint} />
                  <Text style={styles.location} numberOfLines={1}>
                    {store.location}
                  </Text>
                </View>
              ) : null}
            </View>
          </View>

          {store.description ? (
            <Text style={styles.description}>{store.description}</Text>
          ) : null}

          {store.website_url ? (
            <Button
              label="Visit website"
              variant="secondary"
              arrow
              onPress={() => Linking.openURL(store.website_url!).catch(() => {})}
            />
          ) : null}

          {categories.length > 2 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.chips}
            >
              {categories.map((cat) => {
                const active = cat === category;
                return (
                  <Pressable
                    key={cat}
                    onPress={() => setCategory(cat)}
                    accessibilityRole="button"
                    accessibilityState={{ selected: active }}
                    style={[styles.chip, active && styles.chipActive]}
                  >
                    <Text style={[styles.chipText, active && styles.chipTextActive]}>
                      {cat === ALL ? ALL : titleCase(cat)}
                    </Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          ) : null}

          <Text style={styles.count}>
            {visible.length} {visible.length === 1 ? "item" : "items"}
          </Text>
        </View>
      }
      ListEmptyComponent={
        <MessageState
          icon="shirt-outline"
          title="No items here"
          subtitle="This brand has nothing in that category yet."
        />
      }
    />
  );
}

const makeStyles = (c: Palette) => ({
  root: { flex: 1, backgroundColor: c.bg },
  content: { paddingHorizontal: spacing.lg, gap: spacing.md },
  column: { gap: spacing.md },

  header: { gap: spacing.md, paddingBottom: spacing.sm },
  brandRow: { flexDirection: "row" as const, alignItems: "center" as const, gap: spacing.md },
  logoWrap: {
    width: 70,
    height: 70,
    borderRadius: radius.lg,
    backgroundColor: c.accent,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    overflow: "hidden" as const,
  },
  logo: { width: "100%" as const, height: "100%" as const },
  brandBody: { flex: 1 },
  name: { ...typography.title, color: c.text },
  locationRow: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    gap: 4,
    marginTop: 4,
  },
  location: { ...typography.label, color: c.faint, flex: 1 },
  description: { ...typography.body, color: c.muted },

  chips: { gap: spacing.sm, paddingVertical: 2 },
  chip: {
    paddingHorizontal: spacing.md + 2,
    paddingVertical: 10,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surface,
  },
  chipActive: { backgroundColor: c.accent, borderColor: c.accent },
  chipText: {
    ...typography.caption,
    fontFamily: typography.bodyMedium.fontFamily,
    color: c.muted,
  },
  chipTextActive: { color: c.onAccent },

  count: { ...typography.label, color: c.faint },
});
