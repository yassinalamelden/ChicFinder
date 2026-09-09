/**
 * Browse the collaborating Egyptian brands. Public endpoint, so this screen
 * works before the first sign-in too.
 *
 * The search field has two scopes. "Brands" filters the loaded list on the
 * device, which is instant and works offline once the list is in hand.
 * "All items" asks the backend, because the catalog is far too large to hold
 * on the phone, and it is the only way to answer "who sells a linen shirt".
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";

import {
  Button,
  LoadingState,
  MessageState,
  ScreenHeader,
  SearchField,
  Segmented,
} from "../../src/components/ui";
import { ProductCard, type ProductCardData } from "../../src/components/ProductCard";
import { getStores, resolveImageUrl, searchItems } from "../../src/lib/api";
import {
  TAB_BAR_HEIGHT,
  elevation,
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../../src/theme";
import type { Store, StoreItem } from "../../src/types/api";

type Scope = "brands" | "items";

/** Long enough that typing a word is one request, short enough to feel live. */
const DEBOUNCE_MS = 350;

export default function StoresScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);

  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [scope, setScope] = useState<Scope>("brands");
  const [items, setItems] = useState<StoreItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [itemsError, setItemsError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setStores(await getStores());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Guards against a slow early request landing after a later one and
  // overwriting fresher results.
  const requestId = useRef(0);

  useEffect(() => {
    if (scope !== "items") return;
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setItems([]);
      setItemsError(null);
      setItemsLoading(false);
      return;
    }

    const id = ++requestId.current;
    setItemsLoading(true);
    const timer = setTimeout(() => {
      searchItems({ search: trimmed })
        .then((found) => {
          if (id !== requestId.current) return;
          setItems(found);
          setItemsError(null);
        })
        .catch((err: Error) => {
          if (id !== requestId.current) return;
          setItems([]);
          setItemsError(err.message);
        })
        .finally(() => {
          if (id === requestId.current) setItemsLoading(false);
        });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query, scope]);

  const visibleStores = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return stores;
    return stores.filter((store) =>
      [store.name, store.description, store.location]
        .filter(Boolean)
        .some((field) => (field as string).toLowerCase().includes(q))
    );
  }, [stores, query]);

  const cards: ProductCardData[] = items.map((item) => ({
    id: item.id,
    title: item.name,
    brand: item.brand,
    priceEgp: item.price_egp,
    imageUrl: resolveImageUrl(item.image_url),
    productUrl: item.product_url,
  }));

  const header = (
    <View style={styles.headerBlock}>
      <ScreenHeader title="Stores" subtitle="Egyptian brands in the catalog." />
      <SearchField
        value={query}
        onChangeText={setQuery}
        placeholder={scope === "brands" ? "Search brands" : "Search every store"}
      />
      <Segmented<Scope>
        options={[
          { value: "brands", label: "Brands" },
          { value: "items", label: "All items" },
        ]}
        value={scope}
        onChange={setScope}
      />
      {scope === "items" && cards.length > 0 ? (
        <Text style={styles.count}>
          {cards.length} {cards.length === 1 ? "item" : "items"}
        </Text>
      ) : null}
    </View>
  );

  if (loading) return <LoadingState label="Loading stores" />;

  if (error && stores.length === 0) {
    return (
      <MessageState
        icon="cloud-offline-outline"
        tone="error"
        title="Could not load stores"
        subtitle={error}
        action={<Button label="Retry" onPress={load} arrow />}
      />
    );
  }

  const contentStyle = [
    styles.content,
    {
      paddingTop: insets.top + spacing.sm,
      paddingBottom: insets.bottom + TAB_BAR_HEIGHT + spacing.xl,
    },
  ];

  // Remounted per scope: FlatList cannot change numColumns in place.
  if (scope === "items") {
    return (
      <FlatList
        key="items"
        style={styles.root}
        data={cards}
        keyExtractor={(item) => item.id}
        numColumns={2}
        columnWrapperStyle={cards.length ? styles.column : undefined}
        contentContainerStyle={contentStyle}
        showsVerticalScrollIndicator={false}
        keyboardDismissMode="on-drag"
        keyboardShouldPersistTaps="handled"
        renderItem={({ item }) => <ProductCard item={item} />}
        ListHeaderComponent={header}
        ListEmptyComponent={
          itemsLoading ? (
            <LoadingState label="Searching the catalog" />
          ) : itemsError ? (
            <MessageState
              icon="cloud-offline-outline"
              tone="error"
              align="top"
              title="Search failed"
              subtitle={itemsError}
            />
          ) : query.trim().length < 2 ? (
            <MessageState
              icon="search-outline"
              align="top"
              title="Search every store"
              subtitle="Type what you are after: a linen shirt, wide leg denim, a leather bag."
            />
          ) : (
            <MessageState
              icon="shirt-outline"
              align="top"
              title="Nothing matched"
              subtitle={`No item mentions "${query.trim()}" yet.`}
            />
          )
        }
      />
    );
  }

  return (
    <FlatList
      key="brands"
      style={styles.root}
      data={visibleStores}
      keyExtractor={(store) => store.id}
      contentContainerStyle={contentStyle}
      showsVerticalScrollIndicator={false}
      keyboardDismissMode="on-drag"
      keyboardShouldPersistTaps="handled"
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            load();
          }}
          tintColor={colors.muted}
        />
      }
      ListHeaderComponent={header}
      ListEmptyComponent={
        query.trim() ? (
          <MessageState
            icon="search-outline"
            align="top"
            title="No brand matched"
            subtitle="Try the All items scope to search inside every catalog instead."
            action={<Button label="Search all items" onPress={() => setScope("items")} arrow />}
          />
        ) : (
          <MessageState
            icon="storefront-outline"
            align="top"
            title="No stores yet"
            subtitle="Brands are being added. Check back soon."
          />
        )
      }
      renderItem={({ item }) => (
        <Pressable
          onPress={() => router.push(`/store/${item.id}`)}
          accessibilityRole="button"
          accessibilityLabel={`Open ${item.name}`}
          style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
        >
          <View style={styles.logoWrap}>
            {item.logo_url ? (
              <Image source={{ uri: item.logo_url }} style={styles.logo} contentFit="cover" />
            ) : (
              <Ionicons name="storefront-outline" size={22} color={colors.onAccent} />
            )}
          </View>

          <View style={styles.rowBody}>
            <Text style={styles.name} numberOfLines={1}>
              {item.name}
            </Text>
            {item.description ? (
              <Text style={styles.description} numberOfLines={2}>
                {item.description}
              </Text>
            ) : null}
            {item.location ? (
              <View style={styles.locationRow}>
                <Ionicons name="location-outline" size={12} color={colors.faint} />
                <Text style={styles.location} numberOfLines={1}>
                  {item.location}
                </Text>
              </View>
            ) : null}
          </View>

          <Ionicons name="chevron-forward" size={18} color={colors.faint} />
        </Pressable>
      )}
    />
  );
}

const makeStyles = (c: Palette) => ({
  root: { flex: 1, backgroundColor: c.bg },
  content: { paddingHorizontal: spacing.lg, gap: spacing.sm + 2 },
  column: { gap: spacing.md },

  headerBlock: { gap: spacing.sm + 2, paddingBottom: spacing.xs },
  count: { ...typography.label, color: c.faint, marginTop: spacing.xs },

  row: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    gap: spacing.md,
    padding: spacing.md,
    backgroundColor: c.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: c.border,
    ...elevation(c, 1),
  },
  rowPressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },

  logoWrap: {
    width: 54,
    height: 54,
    borderRadius: radius.md,
    backgroundColor: c.accent,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    overflow: "hidden" as const,
  },
  logo: { width: "100%" as const, height: "100%" as const },

  rowBody: { flex: 1, gap: 2 },
  name: { ...typography.title, fontSize: 19, lineHeight: 25, color: c.text },
  description: { ...typography.caption, color: c.muted, marginTop: 2 },
  locationRow: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    gap: 4,
    marginTop: 4,
  },
  location: { ...typography.label, color: c.faint, flex: 1 },
});
