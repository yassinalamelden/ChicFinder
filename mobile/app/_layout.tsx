/**
 * Root layout: fonts, providers, theme chrome, and the gate that decides
 * whether a cold start lands on the welcome screen or the tabs.
 */

import React, { useEffect } from "react";
import { View, StyleSheet } from "react-native";
import { Stack, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import * as SplashScreen from "expo-splash-screen";
import { useFonts } from "expo-font";
import { Anton_400Regular } from "@expo-google-fonts/anton";
import {
  Geist_400Regular,
  Geist_500Medium,
  Geist_600SemiBold,
} from "@expo-google-fonts/geist";

import { AuthProvider, useAuth } from "../src/context/AuthContext";
import { SavedProvider } from "../src/context/SavedContext";
import { colors, typography } from "../src/theme";

SplashScreen.preventAutoHideAsync().catch(() => {});

function RootNavigator({ fontsReady }: { fontsReady: boolean }) {
  const { user, initialising } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  const ready = fontsReady && !initialising;

  useEffect(() => {
    if (!ready) return;

    SplashScreen.hideAsync().catch(() => {});

    const inAuthGroup = segments[0] === "(auth)";

    if (!user && !inAuthGroup) {
      router.replace("/(auth)/welcome");
    } else if (user && inAuthGroup) {
      router.replace("/(tabs)/search");
    }
  }, [user, ready, segments, router]);

  // Holding the splash until the fonts resolve avoids a frame of system-font
  // text, which is jarring when every heading is meant to be Anton.
  if (!ready) return <View style={styles.splash} />;

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg },
        headerTintColor: colors.text,
        headerTitleStyle: typography.heading,
        headerShadowVisible: false,
        contentStyle: { backgroundColor: colors.bg },
      }}
    >
      <Stack.Screen name="(auth)" options={{ headerShown: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen
        name="store/[storeId]"
        options={{ title: "", headerBackTitle: "Back" }}
      />
      <Stack.Screen
        name="delete-account"
        options={{ title: "Delete account", presentation: "modal" }}
      />
    </Stack>
  );
}

export default function RootLayout() {
  const [fontsReady, fontError] = useFonts({
    Anton_400Regular,
    Geist_400Regular,
    Geist_500Medium,
    Geist_600SemiBold,
  });

  // A font that fails to download should degrade to the system face, not trap
  // the user behind a splash screen forever.
  const canRender = fontsReady || Boolean(fontError);

  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <AuthProvider>
          <SavedProvider>
            <StatusBar style="dark" />
            <RootNavigator fontsReady={canRender} />
          </SavedProvider>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  splash: { flex: 1, backgroundColor: colors.bg },
});
