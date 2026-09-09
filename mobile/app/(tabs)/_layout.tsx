import React from "react";
import { Platform, StyleSheet, View } from "react-native";
import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { BlurView } from "expo-blur";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  TAB_BAR_HEIGHT,
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../../src/theme";

/**
 * A floating translucent bar rather than a full-width opaque strip: content
 * scrolls underneath and blurs through it, which is what makes it read as
 * material sitting above the page instead of a web footer bolted to the bottom.
 * Screens pad their scroll content by TAB_BAR_HEIGHT so nothing hides beneath.
 */
function TabIcon({
  name,
  focused,
}: {
  name: keyof typeof Ionicons.glyphMap;
  focused: boolean;
}) {
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  return (
    <View style={[styles.iconPill, focused && styles.iconPillActive]}>
      <Ionicons
        name={name}
        size={21}
        color={focused ? colors.onAccent : colors.muted}
      />
    </View>
  );
}

export default function TabsLayout() {
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.text,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: [
          styles.tabBar,
          { bottom: Math.max(insets.bottom, spacing.sm) },
        ],
        tabBarItemStyle: styles.tabItem,
        tabBarLabelStyle: styles.tabLabel,
        tabBarBackground: () => (
          <View style={styles.glassWrap}>
            <BlurView
              intensity={Platform.OS === "ios" ? 60 : 90}
              tint={colors.blurTint}
              style={StyleSheet.absoluteFill}
            />
            {/* A translucent wash over the blur keeps contrast legible when
                busy product photography scrolls underneath. */}
            <View style={[StyleSheet.absoluteFill, styles.glassTint]} />
          </View>
        ),
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen
        name="search"
        options={{
          title: "Search",
          tabBarIcon: ({ focused }) => <TabIcon name="camera-outline" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="stores"
        options={{
          title: "Stores",
          tabBarIcon: ({ focused }) => <TabIcon name="storefront-outline" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="saved"
        options={{
          title: "Saved",
          tabBarIcon: ({ focused }) => <TabIcon name="heart-outline" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ focused }) => <TabIcon name="person-outline" focused={focused} />,
        }}
      />
    </Tabs>
  );
}

const makeStyles = (c: Palette) => ({
  tabBar: {
    position: "absolute" as const,
    left: spacing.md,
    right: spacing.md,
    height: TAB_BAR_HEIGHT,
    borderRadius: radius.pill,
    borderTopWidth: 0,
    borderWidth: 1,
    borderColor: c.glassBorder,
    backgroundColor: "transparent",
    paddingTop: 6,
    paddingBottom: 0,
    // The blur has to be clipped to the pill, or it paints the corners square.
    overflow: "hidden" as const,
    shadowColor: c.shadow,
    shadowOpacity: 0.14,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 12,
  },
  glassWrap: {
    position: "absolute" as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    overflow: "hidden" as const,
  },
  glassTint: { backgroundColor: c.glass },

  tabItem: { paddingTop: 2 },
  tabLabel: {
    ...typography.label,
    fontSize: 10,
    letterSpacing: 0.2,
    textTransform: "none" as const,
  },
  iconPill: {
    paddingHorizontal: 15,
    paddingVertical: 4,
    borderRadius: radius.pill,
    alignItems: "center" as const,
    justifyContent: "center" as const,
  },
  iconPillActive: { backgroundColor: c.accent },
});
