/**
 * The floating glass tab bar.
 *
 * Built by hand rather than styled through react-navigation's default slots,
 * which is why the previous version looked washed out and slightly off-centre:
 * the library tints icons itself and lays each slot out on its own terms, so a
 * pill drawn inside a slot cannot travel between them.
 *
 * Here the bar owns its layout. One capsule is positioned absolutely over the
 * row and springs to whichever tab is active, so the highlight slides rather
 * than blinking from one tab to the next. Icons are drawn at full strength; the
 * capsule alone carries the active state.
 */

import React, { useEffect, useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from "react-native-reanimated";
import { BlurView } from "expo-blur";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  TAB_BAR_HEIGHT,
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../theme";

const ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  search: "camera",
  stores: "storefront",
  saved: "heart",
  profile: "person",
};

/** The part of react-navigation's tab bar props this component actually uses. */
interface TabBarProps {
  state: {
    index: number;
    routes: Array<{ key: string; name: string }>;
  };
  descriptors: Record<string, { options: { title?: string } }>;
  navigation: {
    emit: (event: {
      type: "tabPress";
      target: string;
      canPreventDefault: true;
    }) => { defaultPrevented: boolean };
    navigate: (name: string) => void;
  };
}

const CAPSULE_WIDTH = 52;
const CAPSULE_HEIGHT = 34;

/** Matches iOS's own spring closely enough to feel native rather than eased. */
const SPRING = { damping: 18, stiffness: 220, mass: 0.7 };

export function TabBar({ state, descriptors, navigation }: TabBarProps) {
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const insets = useSafeAreaInsets();
  const [barWidth, setBarWidth] = useState(0);

  const slot = barWidth / state.routes.length;
  const capsuleX = useSharedValue(0);
  const settled = useSharedValue(false);

  const target = slot > 0 ? state.index * slot + (slot - CAPSULE_WIDTH) / 2 : 0;

  // Driven from an effect rather than during render: writing a shared value
  // while rendering is a side effect, and it makes the first frame race the
  // layout pass. The first placement jumps, every later one springs.
  useEffect(() => {
    if (slot <= 0) return;
    if (!settled.value) {
      capsuleX.value = target;
      settled.value = true;
    } else {
      capsuleX.value = withSpring(target, SPRING);
    }
  }, [target, slot, capsuleX, settled]);

  const capsuleStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: capsuleX.value }],
  }));

  return (
    <View
      style={[styles.wrap, { bottom: Math.max(insets.bottom, spacing.sm) }]}
      onLayout={(e) => setBarWidth(e.nativeEvent.layout.width)}
      pointerEvents="box-none"
    >
      <View style={styles.bar}>
        <BlurView
          intensity={Platform.OS === "ios" ? 70 : 100}
          tint={colors.blurTint}
          style={StyleSheet.absoluteFill}
        />
        {/* A wash over the blur, so labels stay legible when photography
            scrolls underneath. */}
        <View style={[StyleSheet.absoluteFill, styles.tint]} />

        {slot > 0 ? (
          <Animated.View style={[styles.capsule, capsuleStyle]} pointerEvents="none" />
        ) : null}

        <View style={styles.row}>
          {state.routes.map((route, index) => {
            const { options } = descriptors[route.key];
            const label =
              typeof options.title === "string" ? options.title : route.name;
            const focused = state.index === index;
            const icon = ICONS[route.name] ?? "ellipse";

            const onPress = () => {
              const event = navigation.emit({
                type: "tabPress",
                target: route.key,
                canPreventDefault: true,
              });
              if (!focused && !event.defaultPrevented) {
                Haptics.selectionAsync().catch(() => {});
                navigation.navigate(route.name);
              }
            };

            return (
              <Pressable
                key={route.key}
                onPress={onPress}
                accessibilityRole="button"
                accessibilityState={focused ? { selected: true } : {}}
                accessibilityLabel={label}
                style={styles.tab}
              >
                <Ionicons
                  name={focused ? icon : (`${icon}-outline` as keyof typeof Ionicons.glyphMap)}
                  size={21}
                  color={focused ? colors.onAccent : colors.text}
                />
                <Text
                  style={[styles.label, focused ? styles.labelActive : null]}
                  numberOfLines={1}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>
    </View>
  );
}

const makeStyles = (c: Palette) => ({
  wrap: {
    position: "absolute" as const,
    left: spacing.md,
    right: spacing.md,
  },
  bar: {
    height: TAB_BAR_HEIGHT,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: c.glassBorder,
    // The blur has to be clipped to the pill or it paints square corners.
    overflow: "hidden" as const,
    justifyContent: "center" as const,
    shadowColor: c.shadow,
    shadowOpacity: 0.16,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 8 },
    elevation: 12,
  },
  tint: { backgroundColor: c.glass },

  capsule: {
    position: "absolute" as const,
    top: 9,
    width: CAPSULE_WIDTH,
    height: CAPSULE_HEIGHT,
    borderRadius: radius.pill,
    backgroundColor: c.accent,
  },

  row: { flexDirection: "row" as const, alignItems: "center" as const },
  tab: {
    flex: 1,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    gap: 3,
    paddingTop: 4,
  },
  label: {
    ...typography.label,
    fontSize: 10,
    letterSpacing: 0.2,
    textTransform: "none" as const,
    color: c.muted,
  },
  labelActive: {
    color: c.text,
    fontFamily: typography.button.fontFamily,
  },
});
