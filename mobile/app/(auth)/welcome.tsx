/**
 * Welcome and sign-in.
 *
 * Sign in with Apple is listed first on iOS, which is both what Apple's Human
 * Interface Guidelines ask for and what reviewers look at under Guideline 4.8.
 */

import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import * as AppleAuthentication from "expo-apple-authentication";
import * as Linking from "expo-linking";
import Constants from "expo-constants";

import { Button } from "../../src/components/ui";
import { useAuth, AuthError } from "../../src/context/AuthContext";
import { isFirebaseConfigured, missingFirebaseKeys } from "../../src/lib/firebase";
import { colors, radius, spacing, typography } from "../../src/theme";

type Mode = "signIn" | "register";

const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string>;

export default function WelcomeScreen() {
  const insets = useSafeAreaInsets();
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

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + spacing.xl, paddingBottom: insets.bottom + spacing.lg },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.hero}>
          <Text style={styles.wordmark}>Chic Finder</Text>
          <Text style={styles.headline}>
            Find fashion{"\n"}
            <Text style={styles.headlineMuted}>that fits you.</Text>
          </Text>
          <Text style={styles.sub}>
            Snap any outfit. Shop it from Egyptian brands.
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
          {isAppleAvailable ? (
            <AppleAuthentication.AppleAuthenticationButton
              buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
              buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
              cornerRadius={radius.pill}
              style={styles.appleButton}
              onPress={() => run("apple", signInWithApple)}
            />
          ) : null}

          {isGoogleReady ? (
            <Button
              label="Continue with Google"
              icon="logo-google"
              variant="secondary"
              loading={busy === "google"}
              disabled={busy !== null}
              onPress={() => run("google", signInWithGoogle)}
            />
          ) : null}

          {isAppleAvailable || isGoogleReady ? (
            <View style={styles.separator}>
              <View style={styles.line} />
              <Text style={styles.separatorText}>or</Text>
              <View style={styles.line} />
            </View>
          ) : null}

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
            variant="lime"
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
            >
              <Text style={styles.link}>
                {mode === "signIn" ? "Create an account" : "I already have an account"}
              </Text>
            </Pressable>

            {mode === "signIn" ? (
              <Pressable onPress={forgotPassword} accessibilityRole="button">
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

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: {
    paddingHorizontal: spacing.lg + 4,
    gap: spacing.lg + 4,
    flexGrow: 1,
  },

  hero: { gap: spacing.sm + 2 },
  wordmark: {
    ...typography.title,
    fontSize: 15,
    lineHeight: 18,
    letterSpacing: 1.5,
    color: colors.text,
  },
  headline: { ...typography.displayLarge, color: colors.text },
  headlineMuted: { color: colors.faint },
  sub: { ...typography.body, color: colors.muted, maxWidth: 300 },

  configWarning: {
    gap: spacing.xs,
    padding: spacing.md + 2,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.danger,
    backgroundColor: "rgba(166, 61, 43, 0.10)",
  },
  configTitle: {
    ...typography.heading,
    fontSize: 15,
    color: colors.danger,
  },
  configBody: { ...typography.caption, color: colors.text },

  actions: { gap: spacing.sm + 4 },
  appleButton: { height: 54, width: "100%" },

  separator: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  line: { flex: 1, height: 1, backgroundColor: colors.border },
  separatorText: { ...typography.label, color: colors.faint },

  input: {
    minHeight: 54,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.lg + 2,
    color: colors.text,
    ...typography.body,
  },

  switchRow: { flexDirection: "row", justifyContent: "space-between" },
  link: {
    ...typography.caption,
    fontFamily: typography.bodyMedium.fontFamily,
    color: colors.text,
    textDecorationLine: "underline",
  },

  error: { ...typography.caption, color: colors.danger, textAlign: "center" },
  notice: { ...typography.caption, color: colors.text, textAlign: "center" },

  legal: { marginTop: "auto", paddingTop: spacing.lg },
  legalText: {
    ...typography.caption,
    fontSize: 12,
    color: colors.faint,
    textAlign: "center",
  },
});
