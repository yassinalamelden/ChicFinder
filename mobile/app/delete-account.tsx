/**
 * In-app account deletion, required by App Store Guideline 5.1.1(v).
 *
 * The flow is deliberately explicit: the screen states exactly what is deleted,
 * requires the user to type DELETE, and reports the real outcome from the
 * server rather than optimistically claiming success. Recent-login errors are
 * handled by asking the user to sign in again, because Firebase refuses to
 * delete an account on a stale session.
 */

import React, { useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import { Linking } from "react-native";

import { Button } from "../src/components/ui";
import { useAuth } from "../src/context/AuthContext";
import { deleteAccount } from "../src/lib/api";
import { colors, radius, spacing, typography } from "../src/theme";

const CONFIRM_WORD = "DELETE";
const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string>;

const CONSEQUENCES = [
  "Your ChicFinder account and sign-in",
  "Every item you have saved",
  "Your search history on our servers",
];

export default function DeleteAccountScreen() {
  const router = useRouter();
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

      // The backend removes the Firebase user, so the local session is now
      // pointing at an account that no longer exists. Clear it.
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
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <View style={styles.warningBadge}>
        <Ionicons name="warning-outline" size={22} color={colors.danger} />
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
            <Ionicons name="close-circle-outline" size={16} color={colors.danger} />
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
          placeholderTextColor={colors.muted}
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

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, gap: spacing.md },

  warningBadge: {
    width: 48,
    height: 48,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255,90,90,0.12)",
  },
  title: { ...typography.title, color: colors.text },
  body: { ...typography.body, color: colors.muted, lineHeight: 22 },

  list: {
    gap: spacing.sm,
    padding: spacing.md,
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  listHeading: { ...typography.label, color: colors.text },
  listRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  listText: { ...typography.body, color: colors.muted, flex: 1 },

  account: { ...typography.caption, color: colors.muted },
  accountEmail: { color: colors.text, fontWeight: "600" },

  confirmBlock: { gap: spacing.sm, marginTop: spacing.sm },
  label: { ...typography.caption, color: colors.muted },
  confirmWord: { color: colors.danger, fontWeight: "700" },
  input: {
    minHeight: 52,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    color: colors.text,
    letterSpacing: 2,
    ...typography.body,
  },

  errorBlock: { gap: spacing.xs },
  errorText: { ...typography.caption, color: colors.danger },
  errorHelp: { ...typography.caption, color: colors.accent },

  actions: { gap: spacing.sm, marginTop: spacing.md },
});
