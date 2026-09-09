/**
 * Shared building blocks: buttons, screen chrome, empty and error states.
 *
 * The Button here is the brand's signature control: a full pill, optionally
 * carrying a circular arrow badge on the trailing edge. Everything is driven
 * from theme.ts so a palette change never needs a visit to this file.
 */

import React, { type ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { colors, radius, spacing, typography } from "../theme";

// ---------------------------------------------------------------------------
// Button
// ---------------------------------------------------------------------------

type ButtonVariant = "primary" | "lime" | "secondary" | "danger";

interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  icon?: keyof typeof Ionicons.glyphMap;
  /** Adds the circular arrow badge. Use it on forward-moving actions only. */
  arrow?: boolean;
  loading?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  hint?: string;
}

const palette: Record<
  ButtonVariant,
  { bg: string; fg: string; border: string; badge: string }
> = {
  primary: {
    bg: colors.olive,
    fg: colors.onOlive,
    border: colors.olive,
    badge: "rgba(237, 234, 226, 0.18)",
  },
  lime: {
    bg: colors.accent,
    fg: colors.olive,
    border: colors.accent,
    badge: "rgba(30, 35, 0, 0.14)",
  },
  secondary: {
    bg: "transparent",
    fg: colors.text,
    border: colors.border,
    badge: "rgba(52, 49, 48, 0.10)",
  },
  danger: {
    bg: "transparent",
    fg: colors.danger,
    border: colors.danger,
    badge: "rgba(166, 61, 43, 0.12)",
  },
};

export function Button({
  label,
  onPress,
  variant = "primary",
  icon,
  arrow = false,
  loading = false,
  disabled = false,
  style,
  hint,
}: ButtonProps) {
  const isDisabled = disabled || loading;
  const tone = palette[variant];

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={hint}
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      disabled={isDisabled}
      onPress={() => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
        onPress();
      }}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: tone.bg, borderColor: tone.border },
        arrow && styles.buttonWithArrow,
        pressed && !isDisabled && styles.buttonPressed,
        isDisabled && styles.buttonDisabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={tone.fg} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={18} color={tone.fg} /> : null}
          <Text style={[styles.buttonLabel, { color: tone.fg }]}>{label}</Text>
          {arrow ? (
            <View style={[styles.arrowBadge, { backgroundColor: tone.badge }]}>
              <Ionicons name="arrow-forward" size={15} color={tone.fg} />
            </View>
          ) : null}
        </>
      )}
    </Pressable>
  );
}

// ---------------------------------------------------------------------------
// Screen states
// ---------------------------------------------------------------------------

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <View style={styles.centered} accessibilityRole="progressbar">
      <ActivityIndicator color={colors.text} size="large" />
      <Text style={styles.stateSubtitle}>{label}</Text>
    </View>
  );
}

interface MessageStateProps {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle?: string;
  action?: ReactNode;
  tone?: "neutral" | "error";
}

export function MessageState({
  icon,
  title,
  subtitle,
  action,
  tone = "neutral",
}: MessageStateProps) {
  const isError = tone === "error";
  return (
    <View style={styles.centered}>
      <View
        style={[
          styles.stateRing,
          isError && { backgroundColor: "rgba(166, 61, 43, 0.12)" },
        ]}
      >
        <Ionicons
          name={icon}
          size={34}
          color={isError ? colors.danger : colors.olive}
        />
      </View>
      <Text style={styles.stateTitle}>{title}</Text>
      {subtitle ? <Text style={styles.stateSubtitle}>{subtitle}</Text> : null}
      {action ? <View style={styles.stateAction}>{action}</View> : null}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Layout helpers
// ---------------------------------------------------------------------------

export function ScreenHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <View style={styles.header}>
      <Text style={styles.headerTitle} accessibilityRole="header">
        {title}
      </Text>
      {subtitle ? <Text style={styles.headerSubtitle}>{subtitle}</Text> : null}
    </View>
  );
}

/** Small uppercase metadata label. */
export function Label({ children }: { children: ReactNode }) {
  return <Text style={styles.label}>{children}</Text>;
}

export function Divider() {
  return <View style={styles.divider} />;
}

const styles = StyleSheet.create({
  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm + 2,
    minHeight: 54,
    paddingHorizontal: spacing.lg + 4,
    borderRadius: radius.pill,
    borderWidth: 1,
  },
  // The badge is inset from the trailing edge, so that side needs less padding.
  buttonWithArrow: { paddingRight: spacing.sm + 2 },
  buttonPressed: { opacity: 0.78 },
  buttonDisabled: { opacity: 0.4 },
  buttonLabel: typography.button,
  arrowBadge: {
    width: 30,
    height: 30,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },

  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.xl,
    gap: spacing.sm + 2,
  },
  stateRing: {
    width: 84,
    height: 84,
    borderRadius: radius.pill,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.xs,
  },
  stateTitle: { ...typography.title, color: colors.text },
  stateSubtitle: {
    ...typography.body,
    color: colors.muted,
    textAlign: "center",
    maxWidth: 260,
  },
  stateAction: { marginTop: spacing.md, minWidth: 210 },

  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xs,
    paddingBottom: spacing.lg,
  },
  headerTitle: { ...typography.display, color: colors.text },
  headerSubtitle: {
    ...typography.body,
    color: colors.muted,
    marginTop: spacing.sm,
  },

  label: { ...typography.label, color: colors.faint },

  divider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: spacing.md,
  },
});
