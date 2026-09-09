/**
 * In-app account deletion, required by App Store Guideline 5.1.1(v).
 *
 * Deliberately explicit: the screen states what is deleted, requires the user
 * to type DELETE, and reports the real outcome from the server rather than
 * optimistically claiming success.
 */

import React, { useState } from "react";
import { Alert, Linking, ScrollView, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";

import { Button } from "../src/components/ui";
import { useAuth } from "../src/context/AuthContext";
import { deleteAccount } from "../src/lib/api";
import {
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../src/theme";

const CONFIRM_WORD = "DELETE";
const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string>;

const CONSEQUENCES = [
  "Your ChicFinder account and sign-in",
  "Every item you have saved",
  "Your search history on our servers",
];

export default function DeleteAccountScreen() {
  const router = useRouter();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const { user, signOut } = useAuth();
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canDelete = confirmation.trim().toUpperCase() === CONFIRM_WORD && !busy;

  const performDeletion = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await deleteAccount();
      // The backend removes the Firebase user, so the local session now points
      // at an account that no longer exists. Clear it.
      await signOut().catch(() => {});
      Alert.alert("Account deleted", result.message, [
        { text: "OK", onPress: () => router.replace("/(auth)/welcome") },
      ]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const confirmThenDelete = () => {
    Alert.alert(
      "Delete your account?",
      "This cannot be undone. Your account and all your saved items will be permanently removed.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Delete permanently", style: "destructive", onPress: performDeletion },
      ]
    );
  };

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.warningBadge}>
        <Ionicons name="warning-outline" size={26} color={colors.danger} />
      </View>

      <Text style={styles.title}>This is permanent</Text>
      <Text style={styles.body}>
        Deleting your account removes it and its data from ChicFinder for good.
        There is no way to restore it afterwards.
      </Text>

      <View style={styles.list}>
        <Text style={styles.listHeading}>What gets deleted</Text>
        {CONSEQUENCES.map((line) => (
          <View key={line} style={styles.listRow}>
            <Ionicons name="close-circle-outline" size={17} color={colors.danger} />
            <Text style={styles.listText}>{line}</Text>
          </View>
        ))}
      </View>

      {user?.email ? (
        <Text style={styles.account}>
          Signed in as <Text style={styles.accountEmail}>{user.email}</Text>
        </Text>
      ) : null}

      <View style={styles.confirmBlock}>
        <Text style={styles.label}>
          Type <Text style={styles.confirmWord}>{CONFIRM_WORD}</Text> to confirm
        </Text>
        <TextInput
          style={styles.input}
          value={confirmation}
          onChangeText={setConfirmation}
          autoCapitalize="characters"
          autoCorrect={false}
          placeholder={CONFIRM_WORD}
          placeholderTextColor={colors.faint}
          accessibilityLabel={`Type ${CONFIRM_WORD} to confirm account deletion`}
        />
      </View>

      {error ? (
        <View style={styles.errorBlock} accessibilityLiveRegion="polite">
          <Text style={styles.errorText}>{error}</Text>
          <Text
            style={styles.errorHelp}
            onPress={() =>
              Linking.openURL(`mailto:${extra.supportEmail}?subject=Account%20deletion`)
            }
          >
            Still stuck? Email {extra.supportEmail}
          </Text>
        </View>
      ) : null}

      <View style={styles.actions}>
        <Button
          label="Delete my account"
          variant="danger"
          icon="trash-outline"
          loading={busy}
          disabled={!canDelete}
          onPress={confirmThenDelete}
        />
        <Button
          label="Keep my account"
          variant="secondary"
          disabled={busy}
          onPress={() => router.back()}
        />
      </View>
    </ScrollView>
  );
}

const makeStyles = (c: Palette) => ({
  root: { flex: 1, backgroundColor: c.bg },
  content: { padding: spacing.lg + 4, gap: spacing.md + 2 },

  warningBadge: {
    width: 60,
    height: 60,
    borderRadius: radius.pill,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    backgroundColor: c.dangerSoft,
  },
  title: { ...typography.title, color: c.text },
  body: { ...typography.body, color: c.muted },

  list: {
    gap: spacing.sm + 2,
    padding: spacing.md + 4,
    backgroundColor: c.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: c.border,
  },
  listHeading: { ...typography.label, color: c.faint },
  listRow: { flexDirection: "row" as const, alignItems: "center" as const, gap: spacing.sm + 2 },
  listText: { ...typography.body, fontSize: 14, color: c.text, flex: 1 },

  account: { ...typography.caption, color: c.muted },
  accountEmail: { color: c.text, fontFamily: typography.button.fontFamily },

  confirmBlock: { gap: spacing.sm + 2, marginTop: spacing.xs },
  label: { ...typography.caption, color: c.muted },
  confirmWord: { color: c.danger, fontFamily: typography.button.fontFamily },
  input: {
    minHeight: 56,
    backgroundColor: c.surface,
    borderWidth: 1,
    borderColor: c.border,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.lg + 2,
    color: c.text,
    letterSpacing: 2,
    ...typography.body,
  },

  errorBlock: { gap: spacing.xs },
  errorText: { ...typography.caption, color: c.danger },
  errorHelp: {
    ...typography.caption,
    color: c.text,
    textDecorationLine: "underline" as const,
  },

  actions: { gap: spacing.sm + 2, marginTop: spacing.md },
});
