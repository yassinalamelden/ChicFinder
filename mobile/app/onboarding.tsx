/**
 * First-launch walkthrough: three panels, then straight into the camera.
 *
 * It earns its place twice over. A new user learns in ten seconds that this is
 * a camera, not a catalog, and an App Store reviewer opening a cold install
 * learns the same thing, which is the cheapest insurance against a rejection
 * for an app whose purpose is not obvious in the first screen.
 *
 * Skippable from the first panel. A walkthrough you cannot escape is worse than
 * none at all.
 */

import React, { useRef, useState } from "react";
import {
  Pressable,
  ScrollView,
  Text,
  View,
  useWindowDimensions,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { Button } from "../src/components/ui";
import { markOnboarded } from "../src/lib/onboarding";
import {
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../src/theme";

interface Panel {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  body: string;
}

const PANELS: Panel[] = [
  {
    icon: "camera-outline",
    title: "Snap an outfit",
    body: "Photograph anything you like, on the street, on a screen, in your own wardrobe.",
  },
  {
    icon: "sparkles-outline",
    title: "Find it in Egypt",
    body: "ChicFinder reads the pieces in your photo and matches them to Egyptian brands.",
  },
  {
    icon: "heart-outline",
    title: "Keep what you love",
    body: "Save anything to your wishlist, then head to the store when you are ready.",
  },
];

export default function OnboardingScreen() {
  const { width } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const scroller = useRef<ScrollView>(null);
  const [index, setIndex] = useState(0);

  const last = index === PANELS.length - 1;

  const finish = async () => {
    await markOnboarded();
    router.replace("/(tabs)/search");
  };

  const next = () => {
    if (last) return finish();
    Haptics.selectionAsync().catch(() => {});
    scroller.current?.scrollTo({ x: (index + 1) * width, animated: true });
  };

  const onMomentumEnd = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    // Rounding rather than flooring: a drag that lands a pixel short of the
    // boundary should still count as the page it visually settled on.
    const page = Math.round(e.nativeEvent.contentOffset.x / width);
    if (page !== index) setIndex(page);
  };

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.topBar}>
        <Text style={styles.wordmark}>ChicFinder</Text>
        <Pressable
          onPress={finish}
          hitSlop={12}
          accessibilityRole="button"
          accessibilityLabel="Skip the introduction"
        >
          <Text style={styles.skip}>Skip</Text>
        </Pressable>
      </View>

      <ScrollView
        ref={scroller}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={onMomentumEnd}
        style={styles.pager}
      >
        {PANELS.map((panel) => (
          <View key={panel.title} style={[styles.panel, { width }]}>
            <View style={styles.ring}>
              <Ionicons name={panel.icon} size={54} color={colors.onAccent} />
            </View>
            <Text style={styles.title}>{panel.title}</Text>
            <Text style={styles.body}>{panel.body}</Text>
          </View>
        ))}
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: insets.bottom + spacing.lg }]}>
        <View
          style={styles.dots}
          accessibilityRole="progressbar"
          accessibilityLabel={`Step ${index + 1} of ${PANELS.length}`}
        >
          {PANELS.map((panel, i) => (
            <View
              key={panel.title}
              style={[styles.dot, i === index && styles.dotActive]}
            />
          ))}
        </View>

        <Button
          label={last ? "Get started" : "Next"}
          variant="accent"
          arrow
          onPress={next}
        />
      </View>
    </View>
  );
}

const makeStyles = (c: Palette) => ({
  root: { flex: 1, backgroundColor: c.bg },

  topBar: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    justifyContent: "space-between" as const,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  wordmark: { ...typography.title, fontSize: 20, lineHeight: 27, color: c.text },
  skip: { ...typography.bodyMedium, fontSize: 15, color: c.muted },

  pager: { flex: 1 },
  panel: {
    flex: 1,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    paddingHorizontal: spacing.xl,
    gap: spacing.md,
  },
  ring: {
    width: 132,
    height: 132,
    borderRadius: radius.pill,
    backgroundColor: c.accent,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    marginBottom: spacing.lg,
  },
  title: { ...typography.display, color: c.text, textAlign: "center" as const },
  body: {
    ...typography.body,
    fontSize: 16,
    lineHeight: 24,
    color: c.muted,
    textAlign: "center" as const,
    maxWidth: 320,
  },

  footer: { paddingHorizontal: spacing.lg, gap: spacing.lg },
  dots: {
    flexDirection: "row" as const,
    justifyContent: "center" as const,
    gap: spacing.sm,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: radius.pill,
    backgroundColor: c.border,
  },
  // Widened rather than recoloured alone, so the position reads at a glance.
  dotActive: { width: 22, backgroundColor: c.accent },
});
