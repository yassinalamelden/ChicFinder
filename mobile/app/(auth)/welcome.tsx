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
          { paddingTop: insets.top + spacing.xxl, paddingBottom: insets.bottom + spacing.xl },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.hero}>
          <Text style={styles.wordmark}>ChicFinder</Text>
          <Text style={styles.headline}>
            Snap an outfit.{"\n"}
            <Text style={styles.headlineMuted}>Find it in Egypt.</Text>
          </Text>
          <Text style={styles.sub}>
            Photograph any look and ChicFinder matches it against real products
            from Egyptian brands.
          </Text>
        </View>

        <View style={styles.actions}>
          {isAppleAvailable ? (
            <AppleAuthentication.AppleAuthenticationButton
              buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
              buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.WHITE}
              cornerRadius={radius.md}
              style={styles.appleButton}
              onPress={() => run("apple", signInWithApple)}
            />
          ) : null}

          <Button
            label="Continue with Google"
            icon="logo-google"
            variant="secondary"
            loading={busy === "google"}
            disabled={!isGoogleReady || busy !== null}
            onPress={() => run("google", signInWithGoogle)}
          />

          <View style={styles.separator}>
            <View style={styles.line} />
            <Text style={styles.separatorText}>or</Text>
            <View style={styles.line} />
          </View>

          <TextInput
            style={styles.input}
            placeholder="Email"
            placeholderTextColor={colors.muted}
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
            placeholderTextColor={colors.muted}
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
  content: { paddingHorizontal: spacing.lg, gap: spacing.xl, flexGrow: 1 },

  hero: { gap: spacing.sm },
  wordmark: {
    ...typography.label,
    color: colors.accent,
    letterSpacing: 2,
    textTransform: "uppercase",
  },
  headline: { ...typography.display, color: colors.text, lineHeight: 40 },
  headlineMuted: { color: colors.muted },
  sub: { ...typography.body, color: colors.muted, lineHeight: 22, marginTop: spacing.xs },

  actions: { gap: spacing.md },
  appleButton: { height: 52, width: "100%" },

  separator: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  line: { flex: 1, height: 1, backgroundColor: colors.border },
  separatorText: { ...typography.caption, color: colors.muted },

  input: {
    minHeight: 52,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    color: colors.text,
    ...typography.body,
  },

  switchRow: { flexDirection: "row", justifyContent: "space-between" },
  link: { ...typography.caption, color: colors.accent },

  error: { ...typography.caption, color: colors.danger, textAlign: "center" },
  notice: { ...typography.caption, color: colors.accent, textAlign: "center" },

  legal: { marginTop: "auto", paddingTop: spacing.lg },
  legalText: { ...typography.caption, color: colors.muted, textAlign: "center" },
});
