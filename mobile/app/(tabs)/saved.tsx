/**
 * The user's wishlist. Reads through SavedContext so the hearts here and on
 * search results never disagree.
 */

import React, { useCallback, useState } from "react";
import { FlatList, RefreshControl, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";

import { Button, LoadingState, MessageState, ScreenHeader } from "../../src/components/ui";
import { ProductCard, type ProductCardData } from "../../src/components/ProductCard";
import { SignInPrompt } from "../../src/components/SignInPrompt";
import { useSaved } from "../../src/context/SavedContext";
import { resolveImageUrl } from "../../src/lib/api";
import {
  TAB_BAR_HEIGHT,
  spacing,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../../src/theme";

export default function SavedScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const { isSignedIn, items, loading, error, refresh } = useSaved();
  const [refreshing, setRefreshing] = useState(false);

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

  if (!isSignedIn) {
    return (
      <View style={[styles.root, { paddingTop: insets.top + spacing.sm }]}>
        <ScreenHeader title="Saved" />
        <SignInPrompt
          align="top"
          icon="heart-outline"
          title="Keep what you love"
          subtitle="Sign in to save items and find them again on any device."
        />
      </View>
    );
  }

  if (loading && items.length === 0) return <LoadingState label="Loading saved items" />;

  return (
    <View style={[styles.root, { paddingTop: insets.top + spacing.sm }]}>
      <FlatList
        data={cards}
        keyExtractor={(item) => item.id}
        numColumns={2}
        columnWrapperStyle={cards.length ? styles.column : undefined}
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + TAB_BAR_HEIGHT + spacing.xl },
        ]}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => <ProductCard item={item} />}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={async () => {
              setRefreshing(true);
              await refresh();
              setRefreshing(false);
            }}
            tintColor={colors.muted}
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
              action={<Button label="Retry" onPress={refresh} arrow />}
            />
          ) : (
            <MessageState
              icon="heart-outline"
              title="Nothing saved yet"
              subtitle="Tap the heart on any match to keep it here."
              action={
                <Button
                  label="Find something"
                  variant="accent"
                  arrow
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

const makeStyles = (c: Palette) => ({
  root: { flex: 1, backgroundColor: c.bg },
  content: { paddingHorizontal: spacing.lg, gap: spacing.md },
  column: { gap: spacing.md },
});
