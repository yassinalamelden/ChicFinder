/**
 * Account and settings.
 *
 * Works for guests: appearance, the privacy policy and support are all
 * available without an account, and only the parts tied to a person ask for
 * sign-in. For signed-in users Apple checks two things here during review, that
 * account deletion is reachable in-app and that the privacy policy is linked.
 * Neither is buried.
 */

import React, { useState } from "react";
import { Alert, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import * as Application from "expo-application";
import * as Haptics from "expo-haptics";

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
  useThemeMode,
  type Palette,
  type ThemeMode,
} from "../../src/theme";

const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string>;

const MODES: Array<{ value: ThemeMode; label: string; icon: keyof typeof Ionicons.glyphMap }> = [
  { value: "system", label: "System", icon: "phone-portrait-outline" },
  { value: "light", label: "Light", icon: "sunny-outline" },
  { value: "dark", label: "Dark", icon: "moon-outline" },
];

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const { mode, setMode } = useThemeMode();
  const { user, signOut } = useAuth();
  const { items, isSignedIn } = useSaved();
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

      {isSignedIn ? (
        <>
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
        </>
      ) : (
        <View style={styles.guestCard}>
          <View style={styles.guestIcon}>
            <Ionicons name="person-circle-outline" size={26} color={colors.onAccent} />
          </View>
          <Text style={styles.guestTitle}>You are browsing as a guest</Text>
          <Text style={styles.guestBody}>
            Search and stores are open to everyone. Sign in to save items and
            keep them across devices.
          </Text>
          <Button
            label="Sign in"
            variant="accent"
            arrow
            onPress={() => router.push("/(auth)/welcome")}
          />
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Appearance</Text>
        <View style={styles.segment}>
          {MODES.map((option) => {
            const active = mode === option.value;
            return (
              <Pressable
                key={option.value}
                onPress={() => {
                  Haptics.selectionAsync().catch(() => {});
                  setMode(option.value);
                }}
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
                accessibilityLabel={`${option.label} appearance`}
                style={[styles.segmentItem, active && styles.segmentItemActive]}
              >
                <Ionicons
                  name={option.icon}
                  size={17}
                  color={active ? colors.onAccent : colors.muted}
                />
                <Text style={[styles.segmentText, active && styles.segmentTextActive]}>
                  {option.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <View style={styles.group}>
        <Row
          icon="information-circle-outline"
          label="How ChicFinder works"
          // Pushed, not reset. Clearing the flag to replay it would bring the
          // walkthrough back on the next launch if the user backed out here,
          // which is the one thing it must never do.
          onPress={() => router.push("/onboarding")}
        />
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

      {isSignedIn ? (
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
      ) : null}

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

  stat: {
    padding: spacing.lg,
    backgroundColor: c.contrast,
    borderRadius: radius.lg,
    ...elevation(c, 2),
  },
  statValue: { ...typography.display, fontSize: 44, lineHeight: 54, color: c.accent },
  statLabel: { ...typography.label, color: c.onContrastMuted, marginTop: 2 },

  guestCard: {
    gap: spacing.sm + 2,
    padding: spacing.lg,
    backgroundColor: c.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: c.border,
    ...elevation(c, 1),
  },
  guestIcon: {
    width: 48,
    height: 48,
    borderRadius: radius.pill,
    backgroundColor: c.accent,
    alignItems: "center" as const,
    justifyContent: "center" as const,
  },
  guestTitle: { ...typography.title, fontSize: 20, lineHeight: 26, color: c.text },
  guestBody: { ...typography.body, color: c.muted, marginBottom: spacing.xs },

  section: { gap: spacing.sm },
  sectionLabel: { ...typography.label, color: c.faint, paddingLeft: spacing.xs },
  segment: {
    flexDirection: "row" as const,
    gap: 4,
    padding: 4,
    backgroundColor: c.surface,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: c.border,
  },
  segmentItem: {
    flex: 1,
    flexDirection: "row" as const,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    gap: 6,
    paddingVertical: 11,
    borderRadius: radius.pill,
  },
  segmentItemActive: { backgroundColor: c.accent },
  segmentText: {
    ...typography.caption,
    fontFamily: typography.bodyMedium.fontFamily,
    color: c.muted,
  },
  segmentTextActive: { color: c.onAccent },

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
