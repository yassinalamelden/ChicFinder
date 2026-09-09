/**
 * The core screen: take or pick an outfit photo, get matched products.
 *
 * Permissions are requested at the moment the user taps the matching control,
 * never on screen load, and a denial explains how to fix it.
 */

import React, { useCallback, useState } from "react";
import { FlatList, Linking, Platform, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";

import { Button, LoadingState, MessageState, ScreenHeader } from "../../src/components/ui";
import { ProductCard, type ProductCardData } from "../../src/components/ProductCard";
import { searchByPhoto } from "../../src/lib/api";
import {
  TAB_BAR_HEIGHT,
  elevation,
  radius,
  spacing,
  strings,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../../src/theme";
import type { ChicFinderResult } from "../../src/types/api";

type State = "idle" | "searching" | "results" | "error";

const IMAGE_QUALITY = 0.8;

export default function SearchScreen() {
  const insets = useSafeAreaInsets();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);

  const [state, setState] = useState<State>("idle");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [results, setResults] = useState<ChicFinderResult[]>([]);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(async (uri: string, mimeType?: string) => {
    setPhotoUri(uri);
    setState("searching");
    setError(null);
    try {
      const data = await searchByPhoto(uri, mimeType);
      setResults(data.results);
      setElapsedMs(data.processing_time_ms);
      setState("results");
    } catch (err) {
      setError((err as Error).message);
      setState("error");
    }
  }, []);

  const explainDenial = (what: "camera" | "photos") => {
    setError(`ChicFinder needs ${what} access to search. You can turn it on in Settings.`);
    setState("error");
  };

  const takePhoto = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) return explainDenial("camera");
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ["images"],
      quality: IMAGE_QUALITY,
      allowsEditing: true,
    });
    if (result.canceled) return;
    runSearch(result.assets[0].uri, result.assets[0].mimeType);
  };

  const pickPhoto = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return explainDenial("photos");
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: IMAGE_QUALITY,
      allowsEditing: true,
    });
    if (result.canceled) return;
    runSearch(result.assets[0].uri, result.assets[0].mimeType);
  };

  const reset = () => {
    setState("idle");
    setPhotoUri(null);
    setResults([]);
    setError(null);
  };

  const cards: ProductCardData[] = results.map((r) => ({
    id: r.image_id,
    title: r.title,
    brand: r.brand,
    priceEgp: r.price_egp,
    imageUrl: r.image_url,
    productUrl: r.product_url,
    matchScore: r.similarity_score,
    available: r.availability_egypt,
  }));

  return (
    <View style={[styles.root, { paddingTop: insets.top + spacing.sm }]}>
      <FlatList
        data={state === "results" ? cards : []}
        keyExtractor={(item) => item.id}
        numColumns={2}
        columnWrapperStyle={styles.column}
        contentContainerStyle={[
          styles.listContent,
          { paddingBottom: insets.bottom + TAB_BAR_HEIGHT + spacing.xl },
        ]}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => <ProductCard item={item} />}
        ListHeaderComponent={
          <View>
            <ScreenHeader
              title="Find your look"
              subtitle="Photograph an outfit and match it to Egyptian brands."
            />

            {photoUri ? (
              <View style={styles.preview}>
                <Image source={{ uri: photoUri }} style={styles.previewImage} contentFit="cover" />
                <Pressable
                  onPress={reset}
                  style={styles.previewClear}
                  hitSlop={10}
                  accessibilityRole="button"
                  accessibilityLabel="Clear photo and start over"
                >
                  <Ionicons name="close" size={17} color={colors.text} />
                </Pressable>
              </View>
            ) : (
              <Pressable
                onPress={takePhoto}
                accessibilityRole="button"
                accessibilityLabel="Take a photo of an outfit"
                style={({ pressed }) => [styles.dropzone, pressed && styles.dropzonePressed]}
              >
                <View style={styles.dropzoneRing}>
                  <Ionicons name="camera-outline" size={30} color={colors.onAccent} />
                </View>
                <Text style={styles.dropzoneTitle}>Take a photo</Text>
                <Text style={styles.dropzoneSub}>
                  Frame the full outfit for the best matches
                </Text>
              </Pressable>
            )}

            <View style={styles.buttonRow}>
              <Button
                label="Camera"
                icon="camera"
                onPress={takePhoto}
                disabled={state === "searching"}
                style={styles.flexButton}
              />
              <Button
                label="Photos"
                icon="images-outline"
                variant="secondary"
                onPress={pickPhoto}
                disabled={state === "searching"}
                style={styles.flexButton}
              />
            </View>

            {state === "results" ? (
              <Text style={styles.resultsMeta}>
                {results.length} {results.length === 1 ? "match" : "matches"} in{" "}
                {(elapsedMs / 1000).toFixed(1)}s
              </Text>
            ) : null}
          </View>
        }
        ListEmptyComponent={
          state === "searching" ? (
            <LoadingState label="Matching your outfit" />
          ) : state === "error" ? (
            <MessageState
              icon="alert-circle-outline"
              tone="error"
              title="Search failed"
              subtitle={error ?? undefined}
              action={
                <View style={styles.errorActions}>
                  <Button label="Try again" onPress={takePhoto} arrow />
                  {error?.includes("Settings") ? (
                    <Button
                      label="Open Settings"
                      variant="secondary"
                      onPress={() =>
                        Platform.OS === "ios"
                          ? Linking.openURL("app-settings:")
                          : Linking.openSettings()
                      }
                    />
                  ) : null}
                </View>
              }
            />
          ) : state === "results" ? (
            <MessageState
              icon="search-outline"
              title={strings.emptyResultsTitle}
              subtitle={strings.emptyResultsSubtitle}
            />
          ) : null
        }
      />
    </View>
  );
}

const makeStyles = (c: Palette) => ({
  root: { flex: 1, backgroundColor: c.bg },
  listContent: { paddingHorizontal: spacing.lg, gap: spacing.md },
  column: { gap: spacing.md },

  // The heavy block makes the app's core action the anchor of the screen.
  dropzone: {
    alignItems: "center" as const,
    justifyContent: "center" as const,
    gap: spacing.xs + 2,
    paddingVertical: spacing.xxl,
    borderRadius: radius.xl,
    backgroundColor: c.contrast,
    marginBottom: spacing.md,
    ...elevation(c, 2),
  },
  dropzonePressed: { opacity: 0.92, transform: [{ scale: 0.99 }] },
  dropzoneRing: {
    width: 66,
    height: 66,
    borderRadius: radius.pill,
    backgroundColor: c.accent,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    marginBottom: spacing.sm,
  },
  dropzoneTitle: { ...typography.title, fontSize: 22, color: c.onContrast },
  dropzoneSub: { ...typography.caption, color: c.onContrastMuted },

  preview: { position: "relative" as const, marginBottom: spacing.md },
  previewImage: {
    width: "100%" as const,
    aspectRatio: 3 / 4,
    maxHeight: 300,
    borderRadius: radius.xl,
    backgroundColor: c.surfaceAlt,
  },
  previewClear: {
    position: "absolute" as const,
    top: 12,
    right: 12,
    width: 36,
    height: 36,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    borderRadius: radius.pill,
    backgroundColor: c.glass,
    borderWidth: 1,
    borderColor: c.glassBorder,
  },

  buttonRow: { flexDirection: "row" as const, gap: spacing.sm + 2 },
  flexButton: { flex: 1 },

  resultsMeta: {
    ...typography.label,
    color: c.faint,
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  errorActions: { gap: spacing.sm + 2, width: "100%" as const },
});
