/**
 * Browse the collaborating Egyptian brands. Public endpoint, so this screen
 * works before the first sign-in too.
 */

import React, { useCallback, useEffect, useState } from "react";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";

import { Button, LoadingState, MessageState, ScreenHeader } from "../../src/components/ui";
import { getStores } from "../../src/lib/api";
import { colors, radius, spacing, typography } from "../../src/theme";
import type { Store } from "../../src/types/api";

export default function StoresScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <FlatList
      style={styles.root}
      data={stores}
      keyExtractor={(store) => store.id}
      contentContainerStyle={[styles.content, { paddingTop: insets.top + spacing.sm }]}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            load();
          }}
          tintColor={colors.text}
        />
      }
      ListHeaderComponent={
        <ScreenHeader title="Stores" subtitle="Egyptian brands in the catalog." />
      }
      ListEmptyComponent={
        <MessageState
          icon="storefront-outline"
          title="No stores yet"
          subtitle="Brands are being added. Check back soon."
        />
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
              <Ionicons name="storefront-outline" size={22} color={colors.olive} />
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

          <Ionicons name="chevron-forward" size={17} color={colors.faint} />
        </Pressable>
      )}
    />
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xxl,
    gap: spacing.sm + 2,
  },

  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md + 2,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  rowPressed: { opacity: 0.72 },

  logoWrap: {
    width: 52,
    height: 52,
    borderRadius: radius.md,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  logo: { width: "100%", height: "100%" },

  rowBody: { flex: 1, gap: 2 },
  name: { ...typography.title, fontSize: 19, lineHeight: 21, color: colors.text },
  description: { ...typography.caption, color: colors.muted, marginTop: 2 },
  locationRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 4 },
  location: { ...typography.label, color: colors.faint, flex: 1 },
});
