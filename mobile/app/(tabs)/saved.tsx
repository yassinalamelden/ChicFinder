/**
 * The user's wishlist. Reads through SavedContext so the hearts on this screen
 * and on search results never disagree.
 */

import React, { useCallback, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";

import { Button, LoadingState, MessageState, ScreenHeader } from "../../src/components/ui";
import { ProductCard, type ProductCardData } from "../../src/components/ProductCard";
import { useSaved } from "../../src/context/SavedContext";
import { resolveImageUrl } from "../../src/lib/api";
import { colors, spacing } from "../../src/theme";

export default function SavedScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { items, loading, error, refresh } = useSaved();
  const [refreshing, setRefreshing] = useState(false);

  // Coming back from a search where something was saved should show it.
  useFocusEffect(
    useCallback(() => {
      refresh();
    }, [refresh])
  );

  const cards: ProductCardData[] = items.map((item) => ({
    id: item.id,
    title: item.name,
    brand: item.brand,
    priceEgp: item.price_egp,
    imageUrl: resolveImageUrl(item.image_url),
    productUrl: item.product_url,
  }));

  if (loading && items.length === 0) return <LoadingState label="Loading saved items" />;

  return (
    <View style={[styles.root, { paddingTop: insets.top + spacing.sm }]}>
      <FlatList
        data={cards}
        keyExtractor={(item) => item.id}
        numColumns={2}
        columnWrapperStyle={cards.length ? styles.column : undefined}
        contentContainerStyle={styles.content}
        renderItem={({ item }) => <ProductCard item={item} />}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={async () => {
              setRefreshing(true);
              await refresh();
              setRefreshing(false);
            }}
            tintColor={colors.accent}
          />
        }
        ListHeaderComponent={
          <ScreenHeader
            title="Saved"
            subtitle={
              items.length
                ? `${items.length} ${items.length === 1 ? "item" : "items"} you loved.`
                : undefined
            }
          />
        }
        ListEmptyComponent={
          error ? (
            <MessageState
              icon="cloud-offline-outline"
              tone="error"
              title="Could not load your saved items"
              subtitle={error}
              action={<Button label="Retry" onPress={refresh} />}
            />
          ) : (
            <MessageState
              icon="heart-outline"
              title="Nothing saved yet"
              subtitle="Tap the heart on any match to keep it here."
              action={
                <Button
                  label="Find something"
                  onPress={() => router.push("/(tabs)/search")}
                />
              }
            />
          )
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: { paddingHorizontal: spacing.md, paddingBottom: spacing.xxl, gap: spacing.md },
  column: { gap: spacing.md },
});
