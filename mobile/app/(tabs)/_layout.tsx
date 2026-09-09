import React from "react";
import { Tabs } from "expo-router";

import { TabBar } from "../../src/components/TabBar";
import { useTheme } from "../../src/theme";

/**
 * Layout only. The bar itself is a custom component so the active capsule can
 * slide between tabs; see src/components/TabBar.tsx.
 */
export default function TabsLayout() {
  const colors = useTheme();

  return (
    <Tabs
      tabBar={(props) => <TabBar {...props} />}
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen name="search" options={{ title: "Search" }} />
      <Tabs.Screen name="stores" options={{ title: "Stores" }} />
      <Tabs.Screen name="saved" options={{ title: "Saved" }} />
      <Tabs.Screen name="profile" options={{ title: "Profile" }} />
    </Tabs>
  );
}
