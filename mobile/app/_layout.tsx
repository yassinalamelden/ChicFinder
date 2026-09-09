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
import * as SystemUI from "expo-system-ui";
import { useFonts } from "expo-font";
import { Anton_400Regular } from "@expo-google-fonts/anton";
import {
  Geist_400Regular,
  Geist_500Medium,
  Geist_600SemiBold,
} from "@expo-google-fonts/geist";

import { AuthProvider, useAuth } from "../src/context/AuthContext";
import { SavedProvider } from "../src/context/SavedContext";
import { ThemeProvider, typography, useTheme } from "../src/theme";

SplashScreen.preventAutoHideAsync().catch(() => {});

function RootNavigator({ fontsReady }: { fontsReady: boolean }) {
  const { user, initialising } = useAuth();
  const colors = useTheme();
  const segments = useSegments();
  const router = useRouter();

  const ready = fontsReady && !initialising;

  // Paint the window behind the navigator, so switching appearance never
  // flashes the previous palette during a screen transition.
  useEffect(() => {
    SystemUI.setBackgroundColorAsync(colors.bg).catch(() => {});
  }, [colors.bg]);

  useEffect(() => {
    if (!ready) return;

    SplashScreen.hideAsync().catch(() => {});

    // The only redirect left: if the user signs in while the sign-in sheet is
    // open, close it and return them to whatever sent them there. Signed-out
    // users are NOT pushed anywhere; browsing works without an account.
    if (user && segments[0] === "(auth)") {
      if (router.canGoBack()) router.back();
      else router.replace("/(tabs)/search");
    }
  }, [user, ready, segments, router]);

  // Holding the splash until the fonts resolve avoids a frame of system-font
  // text, which is jarring when every heading is meant to be Anton.
  if (!ready) return <View style={[styles.splash, { backgroundColor: colors.bg }]} />;

  return (
    <>
      {/* `auto` flips the status bar between dark and light content to suit
          whichever palette is showing. */}
      <StatusBar style="auto" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.bg },
          headerTintColor: colors.text,
          headerTitleStyle: typography.heading,
          headerShadowVisible: false,
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen
          name="(auth)"
          options={{ headerShown: false, presentation: "modal" }}
        />
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
    </>
  );
}

function Root() {
  const colors = useTheme();
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
    <GestureHandlerRootView style={[styles.root, { backgroundColor: colors.bg }]}>
      <SafeAreaProvider>
        <AuthProvider>
          <SavedProvider>
            <RootNavigator fontsReady={canRender} />
          </SavedProvider>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

export default function RootLayout() {
  return (
    <ThemeProvider>
      <Root />
    </ThemeProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  splash: { flex: 1 },
});
