/**
 * Store detail: brand header plus its catalog, filterable by category.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FlatList,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams, useNavigation } from "expo-router";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";

import { Button, LoadingState, MessageState } from "../../src/components/ui";
import { ProductCard, type ProductCardData } from "../../src/components/ProductCard";
import { getStoreDetail, resolveImageUrl } from "../../src/lib/api";
import { colors, radius, spacing, typography } from "../../src/theme";
import type { Store, StoreItem } from "../../src/types/api";

const ALL = "All";

export default function StoreDetailScreen() {
  const { storeId } = useLocalSearchParams<{ storeId: string }>();
  const navigation = useNavigation();

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
        action={<Button label="Retry" onPress={load} />}
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
      contentContainerStyle={styles.content}
      renderItem={({ item }) => <ProductCard item={item} />}
      ListHeaderComponent={
        <View style={styles.header}>
          <View style={styles.brandRow}>
            <View style={styles.logoWrap}>
              {store.logo_url ? (
                <Image source={{ uri: store.logo_url }} style={styles.logo} contentFit="cover" />
              ) : (
                <Ionicons name="storefront-outline" size={26} color={colors.muted} />
              )}
            </View>
            <View style={styles.brandBody}>
              <Text style={styles.name}>{store.name}</Text>
              {store.location ? (
                <View style={styles.locationRow}>
                  <Ionicons name="location-outline" size={12} color={colors.muted} />
                  <Text style={styles.location}>{store.location}</Text>
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
              icon="open-outline"
              variant="secondary"
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
                      {cat}
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

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: { paddingHorizontal: spacing.md, paddingBottom: spacing.xxl, gap: spacing.md },
  column: { gap: spacing.md },

  header: { gap: spacing.md, paddingBottom: spacing.sm },
  brandRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  logoWrap: {
    width: 64,
    height: 64,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  logo: { width: "100%", height: "100%" },
  brandBody: { flex: 1, gap: 2 },
  name: { ...typography.title, color: colors.text },
  locationRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  location: { ...typography.caption, color: colors.muted },
  description: { ...typography.body, color: colors.muted, lineHeight: 21 },

  chips: { gap: spacing.sm, paddingVertical: 2 },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card,
  },
  chipActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { ...typography.caption, color: colors.muted, fontWeight: "600" },
  chipTextActive: { color: "#0d0d0d" },

  count: { ...typography.caption, color: colors.muted },
});
