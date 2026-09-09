/**
 * Welcome and sign-in.
 *
 * Sign in with Apple is listed first on iOS, which is what Apple's Human
 * Interface Guidelines ask for and what reviewers check under Guideline 4.8.
 *
 * Both social buttons are always visible. When one is not usable yet (Apple
 * needs a development build, Google needs client IDs) tapping it says exactly
 * that, rather than the button vanishing or handing the user an opaque OAuth
 * error page.
 */

import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as AppleAuthentication from "expo-apple-authentication";
import * as Linking from "expo-linking";
import Constants from "expo-constants";

import { Button } from "../../src/components/ui";
import { useAuth, AuthError } from "../../src/context/AuthContext";
import { isFirebaseConfigured, missingFirebaseKeys } from "../../src/lib/firebase";
import {
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../../src/theme";

type Mode = "signIn" | "register";

const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string>;

export default function WelcomeScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const {
    isAppleAvailable,
    isGoogleReady,
    signInWithApple,
    signInWithGoogle,
    signInWithEmail,
    registerWithEmail,
    resetPassword,
  } = useAuth();

  const [mode, setMode] = useState<Mode>("signIn");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<null | "apple" | "google" | "email">(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const run = async (key: "apple" | "google" | "email", fn: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof AuthError ? err.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  };

  const submitEmail = () => {
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    run("email", () =>
      mode === "signIn"
        ? signInWithEmail(email, password)
        : registerWithEmail(email, password)
    );
  };

  const forgotPassword = async () => {
    if (!email.trim()) {
      setError("Enter your email address first, then tap reset.");
      return;
    }
    await run("email", async () => {
      await resetPassword(email);
      setNotice("Password reset email sent. Check your inbox.");
    });
  };

  const appleUnavailable = () =>
    setError(
      "Sign in with Apple needs a development build. It will not run inside Expo Go."
    );

  const googleUnavailable = () =>
    setError(
      "Google sign-in is not set up yet. Add the EXPO_PUBLIC_GOOGLE_* client IDs to mobile/.env."
    );

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={[
          styles.content,
          {
            paddingTop: insets.top + spacing.lg,
            paddingBottom: insets.bottom + spacing.lg,
          },
        ]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.topBar}>
          <Text style={styles.wordmark}>Chic Finder</Text>
          {router.canGoBack() ? (
            <Pressable
              onPress={() => router.back()}
              hitSlop={12}
              accessibilityRole="button"
              accessibilityLabel="Close and keep browsing"
              style={styles.close}
            >
              <Ionicons name="close" size={20} color={colors.text} />
            </Pressable>
          ) : null}
        </View>

        <View style={styles.hero}>
          <Text style={styles.headline}>
            Snap an outfit.{"\n"}
            <Text style={styles.headlineMuted}>Find it in Egypt.</Text>
          </Text>
          <Text style={styles.sub}>
            Photograph any look and match it to real products from Egyptian brands.
          </Text>
        </View>

        {!isFirebaseConfigured ? (
          <View style={styles.configWarning}>
            <Text style={styles.configTitle}>Sign-in is not configured</Text>
            <Text style={styles.configBody}>
              Add real values to mobile/.env from your Firebase console, then
              restart Expo. Missing: {missingFirebaseKeys.join(", ")}
            </Text>
          </View>
        ) : null}

        <View style={styles.actions}>
          {Platform.OS === "ios" && isAppleAvailable ? (
            <AppleAuthentication.AppleAuthenticationButton
              buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
              buttonStyle={
                colors.blurTint === "dark"
                  ? AppleAuthentication.AppleAuthenticationButtonStyle.WHITE
                  : AppleAuthentication.AppleAuthenticationButtonStyle.BLACK
              }
              cornerRadius={radius.pill}
              style={styles.appleButton}
              onPress={() => run("apple", signInWithApple)}
            />
          ) : Platform.OS === "ios" ? (
            <Button
              label="Continue with Apple"
              icon="logo-apple"
              variant="primary"
              disabled={busy !== null}
              onPress={appleUnavailable}
            />
          ) : null}

          <Button
            label="Continue with Google"
            icon="logo-google"
            variant="secondary"
            loading={busy === "google"}
            disabled={busy !== null}
            onPress={() =>
              isGoogleReady ? run("google", signInWithGoogle) : googleUnavailable()
            }
          />

          <View style={styles.separator}>
            <View style={styles.line} />
            <Text style={styles.separatorText}>or</Text>
            <View style={styles.line} />
          </View>

          <TextInput
            style={styles.input}
            placeholder="Email"
            placeholderTextColor={colors.faint}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            textContentType="emailAddress"
            accessibilityLabel="Email address"
          />
          <TextInput
            style={styles.input}
            placeholder="Password"
            placeholderTextColor={colors.faint}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoCapitalize="none"
            textContentType={mode === "signIn" ? "password" : "newPassword"}
            accessibilityLabel="Password"
            onSubmitEditing={submitEmail}
          />

          <Button
            label={mode === "signIn" ? "Sign in" : "Create account"}
            variant="accent"
            arrow
            loading={busy === "email"}
            disabled={busy !== null}
            onPress={submitEmail}
          />

          <View style={styles.switchRow}>
            <Pressable
              onPress={() => {
                setMode(mode === "signIn" ? "register" : "signIn");
                setError(null);
                setNotice(null);
              }}
              accessibilityRole="button"
              hitSlop={8}
            >
              <Text style={styles.link}>
                {mode === "signIn" ? "Create an account" : "I already have an account"}
              </Text>
            </Pressable>

            {mode === "signIn" ? (
              <Pressable onPress={forgotPassword} accessibilityRole="button" hitSlop={8}>
                <Text style={styles.link}>Reset password</Text>
              </Pressable>
            ) : null}
          </View>

          {error ? (
            <Text style={styles.error} accessibilityLiveRegion="polite">
              {error}
            </Text>
          ) : null}
          {notice ? (
            <Text style={styles.notice} accessibilityLiveRegion="polite">
              {notice}
            </Text>
          ) : null}
        </View>

        <Pressable
          onPress={() => Linking.openURL(extra.privacyPolicyUrl)}
          accessibilityRole="link"
          style={styles.legal}
        >
          <Text style={styles.legalText}>
            By continuing you agree to our Terms and Privacy Policy.
          </Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const makeStyles = (c: Palette) => ({
  root: { flex: 1, backgroundColor: c.bg },
  content: {
    paddingHorizontal: spacing.lg + 4,
    gap: spacing.lg,
    flexGrow: 1,
  },

  topBar: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    justifyContent: "space-between" as const,
  },
  close: {
    width: 36,
    height: 36,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    borderRadius: radius.pill,
    backgroundColor: c.surface,
    borderWidth: 1,
    borderColor: c.border,
  },
  hero: { gap: spacing.sm },
  wordmark: {
    ...typography.label,
    fontSize: 12,
    letterSpacing: 2.4,
    color: c.faint,
  },
  headline: { ...typography.displayLarge, color: c.text },
  headlineMuted: { color: c.accent },
  sub: { ...typography.body, color: c.muted, maxWidth: 310 },

  actions: { gap: spacing.sm + 4 },
  appleButton: { height: 56, width: "100%" as const },

  separator: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    gap: spacing.md,
    paddingVertical: spacing.xs,
  },
  line: { flex: 1, height: 1, backgroundColor: c.border },
  separatorText: { ...typography.label, color: c.faint },

  input: {
    minHeight: 56,
    backgroundColor: c.surface,
    borderWidth: 1,
    borderColor: c.border,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.lg + 2,
    color: c.text,
    ...typography.body,
  },

  switchRow: {
    flexDirection: "row" as const,
    justifyContent: "space-between" as const,
    paddingTop: spacing.xs,
  },
  link: {
    ...typography.caption,
    fontFamily: typography.bodyMedium.fontFamily,
    color: c.text,
    textDecorationLine: "underline" as const,
  },

  error: { ...typography.caption, color: c.danger, textAlign: "center" as const },
  notice: { ...typography.caption, color: c.text, textAlign: "center" as const },

  configWarning: {
    gap: spacing.xs,
    padding: spacing.md + 2,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: c.danger,
    backgroundColor: c.dangerSoft,
  },
  configTitle: { ...typography.heading, fontSize: 15, color: c.danger },
  configBody: { ...typography.caption, color: c.text },

  legal: { marginTop: "auto" as const, paddingTop: spacing.lg },
  legalText: {
    ...typography.caption,
    fontSize: 12,
    color: c.faint,
    textAlign: "center" as const,
  },
});
