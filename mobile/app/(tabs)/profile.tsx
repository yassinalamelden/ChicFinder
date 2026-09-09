/**
 * Account screen.
 *
 * Apple checks two things here during review: that a signed-in user can delete
 * their account without leaving the app, and that the privacy policy is
 * reachable. Both live on this screen, and neither is buried.
 */

import React, { useState } from "react";
import { Alert, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import * as Application from "expo-application";

import { Button, ScreenHeader } from "../../src/components/ui";
import { useAuth } from "../../src/context/AuthContext";
import { useSaved } from "../../src/context/SavedContext";
import {
  TAB_BAR_HEIGHT,
  elevation,
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../../src/theme";

const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string>;

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
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
        {
          paddingTop: insets.top + spacing.sm,
          paddingBottom: insets.bottom + TAB_BAR_HEIGHT + spacing.xl,
        },
      ]}
      showsVerticalScrollIndicator={false}
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

      <View style={styles.stat}>
        <Text style={styles.statValue}>{items.length}</Text>
        <Text style={styles.statLabel}>Saved items</Text>
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
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
    >
      <Ionicons name={icon} size={19} color={colors.text} />
      <Text style={styles.rowLabel}>{label}</Text>
      <Ionicons name="chevron-forward" size={18} color={colors.faint} />
    </Pressable>
  );
}

const makeStyles = (c: Palette) => ({
  root: { flex: 1, backgroundColor: c.bg },
  content: { paddingHorizontal: spacing.lg, gap: spacing.lg },

  identity: { flexDirection: "row" as const, alignItems: "center" as const, gap: spacing.md },
  avatar: {
    width: 68,
    height: 68,
    borderRadius: radius.pill,
    backgroundColor: c.accent,
    alignItems: "center" as const,
    justifyContent: "center" as const,
  },
  avatarText: { ...typography.title, fontSize: 28, color: c.onAccent },
  identityBody: { flex: 1, gap: 2 },
  name: { ...typography.title, color: c.text },
  email: { ...typography.caption, color: c.muted },

  // The one number on the screen gets the heavy block, so it reads as a stat
  // rather than another row of text.
  stat: {
    padding: spacing.lg,
    backgroundColor: c.contrast,
    borderRadius: radius.lg,
    ...elevation(c, 2),
  },
  statValue: { ...typography.display, fontSize: 44, lineHeight: 54, color: c.accent },
  statLabel: { ...typography.label, color: c.onContrastMuted, marginTop: 2 },

  group: { gap: spacing.sm + 2 },
  row: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    gap: spacing.md,
    minHeight: 58,
    paddingHorizontal: spacing.md + 4,
    backgroundColor: c.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: c.border,
    ...elevation(c, 1),
  },
  rowPressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  rowLabel: { ...typography.body, color: c.text, flex: 1 },

  version: { ...typography.label, color: c.faint, textAlign: "center" as const },
});
