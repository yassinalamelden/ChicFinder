/**
 * Account screen.
 *
 * Apple checks two things here during review: that a signed-in user can delete
 * their account without leaving the app, and that the privacy policy is
 * reachable. Both live on this screen, and neither is buried.
 */

import React, { useState } from "react";
import { Alert, Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import * as Application from "expo-application";

import { Button, ScreenHeader } from "../../src/components/ui";
import { useAuth } from "../../src/context/AuthContext";
import { useSaved } from "../../src/context/SavedContext";
import { colors, radius, spacing, typography } from "../../src/theme";

const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string>;

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user, signOut } = useAuth();
  const { items } = useSaved();
  const [signingOut, setSigningOut] = useState(false);

  const initial = (user?.displayName ?? user?.email ?? "?").trim().charAt(0).toUpperCase();

  const confirmSignOut = () => {
    Alert.alert("Sign out?", "You can sign back in any time.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign out",
        style: "destructive",
        onPress: async () => {
          setSigningOut(true);
          try {
            await signOut();
          } finally {
            setSigningOut(false);
          }
        },
      },
    ]);
  };

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={[
        styles.content,
        { paddingTop: insets.top + spacing.sm, paddingBottom: insets.bottom + spacing.xxl },
      ]}
    >
      <ScreenHeader title="Profile" />

      <View style={styles.identity}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initial}</Text>
        </View>
        <View style={styles.identityBody}>
          <Text style={styles.name} numberOfLines={1}>
            {user?.displayName ?? "ChicFinder user"}
          </Text>
          <Text style={styles.email} numberOfLines={1}>
            {user?.email ?? "Signed in"}
          </Text>
        </View>
      </View>

      <View style={styles.statsRow}>
        <View style={styles.stat}>
          <Text style={styles.statValue}>{items.length}</Text>
          <Text style={styles.statLabel}>Saved items</Text>
        </View>
      </View>

      <View style={styles.group}>
        <Row
          icon="shield-checkmark-outline"
          label="Privacy Policy"
          onPress={() => Linking.openURL(extra.privacyPolicyUrl)}
        />
        <Row
          icon="mail-outline"
          label="Contact support"
          onPress={() =>
            Linking.openURL(`mailto:${extra.supportEmail}?subject=ChicFinder%20support`)
          }
        />
      </View>

      <View style={styles.group}>
        <Button
          label="Sign out"
          variant="secondary"
          icon="log-out-outline"
          loading={signingOut}
          onPress={confirmSignOut}
        />
        <Button
          label="Delete account"
          variant="danger"
          icon="trash-outline"
          hint="Permanently deletes your account and saved items"
          onPress={() => router.push("/delete-account")}
        />
      </View>

      <Text style={styles.version}>
        ChicFinder {Application.nativeApplicationVersion ?? "1.0.0"}
        {Application.nativeBuildVersion ? ` (${Application.nativeBuildVersion})` : ""}
      </Text>
    </ScrollView>
  );
}

function Row({
  icon,
  label,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
    >
      <Ionicons name={icon} size={19} color={colors.text} />
      <Text style={styles.rowLabel}>{label}</Text>
      <Ionicons name="chevron-forward" size={17} color={colors.faint} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: { paddingHorizontal: spacing.lg, gap: spacing.xl - 8 },

  identity: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  avatar: {
    width: 68,
    height: 68,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { ...typography.title, fontSize: 30, color: colors.olive },
  identityBody: { flex: 1, gap: 3 },
  name: { ...typography.title, color: colors.text },
  email: { ...typography.caption, color: colors.muted },

  statsRow: { flexDirection: "row", gap: spacing.md },
  // An olive block, so the one number on the screen carries some weight.
  stat: {
    flex: 1,
    padding: spacing.md + 4,
    backgroundColor: colors.olive,
    borderRadius: radius.lg,
  },
  statValue: { ...typography.display, fontSize: 40, lineHeight: 40, color: colors.accent },
  statLabel: { ...typography.label, color: colors.onOliveMuted, marginTop: 6 },

  group: { gap: spacing.sm + 2 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    minHeight: 58,
    paddingHorizontal: spacing.md + 4,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  rowPressed: { opacity: 0.72 },
  rowLabel: { ...typography.body, color: colors.text, flex: 1 },

  version: { ...typography.label, color: colors.faint, textAlign: "center" },
});
