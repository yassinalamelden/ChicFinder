/**
 * The core screen: take or pick an outfit photo, get matched products.
 *
 * Permission handling matters for App Store review. Both the camera and the
 * library ask only at the moment the user taps the corresponding button, never
 * on screen load, and a denial explains how to fix it instead of failing quietly.
 */

import React, { useCallback, useState } from "react";
import {
  FlatList,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";

import { Button, LoadingState, MessageState, ScreenHeader } from "../../src/components/ui";
import { ProductCard, type ProductCardData } from "../../src/components/ProductCard";
import { searchByPhoto } from "../../src/lib/api";
import { colors, radius, spacing, strings, typography } from "../../src/theme";
import type { ChicFinderResult } from "../../src/types/api";

type State = "idle" | "searching" | "results" | "error";

/** Compression, so a 12MP photo does not stall the upload on mobile data. */
const IMAGE_QUALITY = 0.8;

export default function SearchScreen() {
  const insets = useSafeAreaInsets();
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
    setError(
      `ChicFinder needs ${what} access to search. You can turn it on in Settings.`
    );
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
    const asset = result.assets[0];
    runSearch(asset.uri, asset.mimeType);
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
    const asset = result.assets[0];
    runSearch(asset.uri, asset.mimeType);
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
        contentContainerStyle={styles.listContent}
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
                style={styles.dropzone}
                accessibilityRole="button"
                accessibilityLabel="Take a photo of an outfit"
              >
                <View style={styles.dropzoneRing}>
                  <Ionicons name="camera-outline" size={28} color={colors.olive} />
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

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  listContent: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xxl,
    gap: spacing.md,
  },
  column: { gap: spacing.md },

  // The olive block makes the app's core action the heaviest thing on screen,
  // and echoes the dark contrast sections on the marketing site.
  dropzone: {
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.xs + 2,
    paddingVertical: spacing.xxl,
    borderRadius: radius.xl,
    backgroundColor: colors.olive,
    marginBottom: spacing.md,
  },
  dropzoneRing: {
    width: 64,
    height: 64,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.xs + 2,
  },
  dropzoneTitle: { ...typography.title, fontSize: 24, color: colors.onOlive },
  dropzoneSub: { ...typography.caption, color: colors.onOliveMuted },

  preview: { position: "relative", marginBottom: spacing.md },
  previewImage: {
    width: "100%",
    aspectRatio: 3 / 4,
    maxHeight: 300,
    borderRadius: radius.xl,
    backgroundColor: "#c9c0b2",
  },
  previewClear: {
    position: "absolute",
    top: 12,
    right: 12,
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
    backgroundColor: "rgba(242, 239, 230, 0.92)",
  },

  buttonRow: { flexDirection: "row", gap: spacing.sm + 2 },
  flexButton: { flex: 1 },

  resultsMeta: {
    ...typography.label,
    color: colors.faint,
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  errorActions: { gap: spacing.sm + 2, width: "100%" },
});
