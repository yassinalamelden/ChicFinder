/**
 * The core screen: take or pick an outfit photo, get matched products.
 *
 * It also accepts words. A photo is the point of the product, but it is not
 * always available: the camera roll has nothing useful, the lighting is wrong,
 * or the person already knows they want a linen shirt. Typing runs against the
 * same catalog endpoint the Stores tab uses, so the app always has something to
 * do rather than dead-ending on a failed match.
 *
 * Permissions are requested at the moment the user taps the matching control,
 * never on screen load, and a denial explains how to fix it.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FlatList, Linking, Platform, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";

import {
  Button,
  LoadingState,
  MessageState,
  ScreenHeader,
  SearchField,
} from "../../src/components/ui";
import { ProductCard, type ProductCardData } from "../../src/components/ProductCard";
import { RecentSearches } from "../../src/components/RecentSearches";
import {
  DEFAULT_FILTERS,
  ResultFilters,
  applyFilters,
  type FilterState,
} from "../../src/components/ResultFilters";
import { resolveImageUrl, searchByPhoto, searchItems } from "../../src/lib/api";
import {
  addRecent,
  clearRecent,
  dropRecent,
  loadRecent,
  type RecentSearch,
} from "../../src/lib/recentSearches";
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
import type { ChicFinderResult, StoreItem } from "../../src/types/api";

type State = "idle" | "searching" | "results" | "error";

const IMAGE_QUALITY = 0.8;

/** Long enough that typing a word is one request, short enough to feel live. */
const DEBOUNCE_MS = 350;

/** Below this a query matches most of the catalog, which is not a search. */
const MIN_QUERY = 2;

export default function SearchScreen() {
  const insets = useSafeAreaInsets();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);

  const [state, setState] = useState<State>("idle");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [results, setResults] = useState<ChicFinderResult[]>([]);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<RecentSearch[]>([]);

  const [query, setQuery] = useState("");
  const [textItems, setTextItems] = useState<StoreItem[]>([]);
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);

  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  const textActive = query.trim().length >= MIN_QUERY;

  useEffect(() => {
    loadRecent().then(setRecent);
  }, []);

  const runSearch = useCallback(async (uri: string, mimeType?: string) => {
    setPhotoUri(uri);
    setState("searching");
    setError(null);
    setFilters(DEFAULT_FILTERS);
    try {
      const data = await searchByPhoto(uri, mimeType);
      setResults(data.results);
      setElapsedMs(data.processing_time_ms);
      setState("results");
      // Only a search that actually returned earns a place in the strip: a
      // failed one is not worth offering to repeat.
      setRecent(await addRecent(uri, data.results.length));
    } catch (err) {
      setError((err as Error).message);
      setState("error");
    }
  }, []);

  const forgetRecent = useCallback((uri: string) => {
    dropRecent(uri).then(setRecent);
  }, []);

  // Guards against a slow early request landing after a later one and
  // overwriting fresher results.
  const requestId = useRef(0);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < MIN_QUERY) {
      setTextItems([]);
      setTextError(null);
      setTextLoading(false);
      return;
    }

    const id = ++requestId.current;
    setTextLoading(true);
    const timer = setTimeout(() => {
      searchItems({ search: trimmed })
        .then((found) => {
          if (id !== requestId.current) return;
          setTextItems(found);
          setTextError(null);
        })
        .catch((err: Error) => {
          if (id !== requestId.current) return;
          setTextItems([]);
          setTextError(err.message);
        })
        .finally(() => {
          if (id === requestId.current) setTextLoading(false);
        });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query]);

  // A new query is a new set of brands, so an old brand filter would silently
  // hide everything.
  useEffect(() => {
    setFilters(DEFAULT_FILTERS);
  }, [query]);

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
    setFilters(DEFAULT_FILTERS);
  };

  const photoCards: ProductCardData[] = useMemo(
    () =>
      results.map((r) => ({
        id: r.image_id,
        title: r.title,
        brand: r.brand,
        priceEgp: r.price_egp,
        imageUrl: r.image_url,
        productUrl: r.product_url,
        matchScore: r.similarity_score,
        available: r.availability_egypt,
      })),
    [results]
  );

  const textCards: ProductCardData[] = useMemo(
    () =>
      textItems.map((item) => ({
        id: item.id,
        title: item.name,
        brand: item.brand,
        priceEgp: item.price_egp,
        imageUrl: resolveImageUrl(item.image_url),
        productUrl: item.product_url,
      })),
    [textItems]
  );

  const source = textActive ? textCards : state === "results" ? photoCards : [];
  const cards = useMemo(() => applyFilters(source, filters), [source, filters]);

  return (
    <View style={[styles.root, { paddingTop: insets.top + spacing.sm }]}>
      <FlatList
        data={cards}
        keyExtractor={(item) => item.id}
        numColumns={2}
        columnWrapperStyle={cards.length ? styles.column : undefined}
        contentContainerStyle={[
          styles.listContent,
          { paddingBottom: insets.bottom + TAB_BAR_HEIGHT + spacing.xl },
        ]}
        showsVerticalScrollIndicator={false}
        keyboardDismissMode="on-drag"
        keyboardShouldPersistTaps="handled"
        renderItem={({ item }) => <ProductCard item={item} />}
        ListHeaderComponent={
          <View>
            <ScreenHeader
              flush
              title="Find your look"
              subtitle="Photograph an outfit and match it to Egyptian brands."
            />

            <SearchField
              value={query}
              onChangeText={setQuery}
              placeholder="Or search by name, colour, brand"
              style={styles.field}
            />

            {/* Typing takes the screen over: the camera block is a large target
                that would push every text result below the fold. */}
            {textActive ? null : (
              <>
                {photoUri ? (
                  <View style={styles.preview}>
                    <Image
                      source={{ uri: photoUri }}
                      style={styles.previewImage}
                      contentFit="cover"
                    />
                    <Pressable
                      onPress={reset}
                      style={styles.previewClear}
                      hitSlop={10}
                      accessibilityRole="button"
                      accessibilityLabel="Clear photo and start over"
                    >
                      <Ionicons name="close" size={18} color="#edeae2" />
                    </Pressable>
                  </View>
                ) : (
                  <Pressable
                    onPress={takePhoto}
                    accessibilityRole="button"
                    accessibilityLabel="Take a photo of an outfit"
                    style={({ pressed }) => [
                      styles.dropzone,
                      pressed && styles.dropzonePressed,
                    ]}
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

                <Button
                  label="Choose from photos"
                  icon="images-outline"
                  variant="secondary"
                  onPress={pickPhoto}
                  disabled={state === "searching"}
                />
              </>
            )}

            {!textActive && state === "idle" ? (
              <>
                <View style={styles.steps}>
                  {["Snap", "Match", "Shop"].map((step, i) => (
                    <View key={step} style={styles.step}>
                      <View style={styles.stepDot}>
                        <Text style={styles.stepNumber}>{i + 1}</Text>
                      </View>
                      <Text style={styles.stepLabel}>{step}</Text>
                      {i < 2 ? <View style={styles.stepLine} /> : null}
                    </View>
                  ))}
                </View>

                <RecentSearches
                  items={recent}
                  onSelect={(uri) => runSearch(uri)}
                  onMissing={forgetRecent}
                  onClear={() => {
                    clearRecent();
                    setRecent([]);
                  }}
                />
              </>
            ) : null}

            {textActive ? (
              textLoading ? null : (
                <Text style={styles.resultsMeta}>
                  {cards.length} {cards.length === 1 ? "item" : "items"} for
                  {` "${query.trim()}"`}
                </Text>
              )
            ) : state === "results" ? (
              <Text style={styles.resultsMeta}>
                {cards.length} {cards.length === 1 ? "match" : "matches"} in{" "}
                {(elapsedMs / 1000).toFixed(1)}s
              </Text>
            ) : null}

            <ResultFilters
              cards={source}
              value={filters}
              onChange={setFilters}
              hasMatchScores={!textActive}
            />
          </View>
        }
        ListEmptyComponent={
          textActive ? (
            textLoading ? (
              <LoadingState label="Searching the catalog" />
            ) : textError ? (
              <MessageState
                icon="cloud-offline-outline"
                tone="error"
                align="top"
                title="Search failed"
                subtitle={textError}
              />
            ) : (
              <MessageState
                icon="shirt-outline"
                align="top"
                title="Nothing matched"
                subtitle={`No item mentions "${query.trim()}" yet. Try a photo instead.`}
              />
            )
          ) : state === "searching" ? (
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

  field: { marginBottom: spacing.md },

  // The heavy block makes the app's core action the anchor of the screen.
  dropzone: {
    alignItems: "center" as const,
    justifyContent: "center" as const,
    gap: spacing.xs + 2,
    paddingVertical: 56,
    paddingHorizontal: spacing.lg,
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

  /**
   * The frame owns the size and the clipping, and the photo fills it.
   *
   * An earlier version put `aspectRatio` and `maxHeight` on the image itself.
   * Yoga resolves aspectRatio against the clamped height, so the photo came out
   * 225pt wide inside a full-width row: the picture sat left of the page and
   * the clear button, anchored to the row rather than to the photo, floated off
   * to its right. One box with the ratio on it fixes both at once.
   */
  preview: {
    position: "relative" as const,
    width: "100%" as const,
    aspectRatio: 4 / 5,
    borderRadius: radius.xl,
    overflow: "hidden" as const,
    backgroundColor: c.surfaceAlt,
    marginBottom: spacing.md,
    ...elevation(c, 2),
  },
  previewImage: { width: "100%" as const, height: "100%" as const },
  previewClear: {
    position: "absolute" as const,
    top: spacing.sm + 2,
    right: spacing.sm + 2,
    width: 38,
    height: 38,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    borderRadius: radius.pill,
    // Sits over photography, so it carries its own ground rather than the
    // page's: a translucent tint would vanish against a light shot.
    backgroundColor: "rgba(20, 21, 15, 0.55)",
    borderWidth: 1,
    borderColor: "rgba(237, 234, 226, 0.35)",
  },

  resultsMeta: {
    ...typography.label,
    color: c.faint,
    marginTop: spacing.lg,
  },
  steps: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    marginTop: spacing.lg,
  },
  step: { flexDirection: "row" as const, alignItems: "center" as const },
  stepDot: {
    width: 22,
    height: 22,
    borderRadius: radius.pill,
    backgroundColor: c.accentSoft,
    alignItems: "center" as const,
    justifyContent: "center" as const,
  },
  stepNumber: { ...typography.label, fontSize: 10, color: c.text },
  stepLabel: { ...typography.label, color: c.muted, marginLeft: 6 },
  stepLine: {
    width: 26,
    height: 1,
    backgroundColor: c.border,
    marginHorizontal: spacing.sm,
  },

  errorActions: { gap: spacing.sm + 2, width: "100%" as const },
});
