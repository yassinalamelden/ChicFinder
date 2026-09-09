/**
 * Small shared building blocks: buttons, screen chrome, empty and error states.
 * Everything here is theme-driven so the app stays visually consistent.
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

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  icon?: keyof typeof Ionicons.glyphMap;
  loading?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  /** Accessibility hint for screen readers, when the label alone is not enough. */
  hint?: string;
}

export function Button({
  label,
  onPress,
  variant = "primary",
  icon,
  loading = false,
  disabled = false,
  style,
  hint,
}: ButtonProps) {
  const isDisabled = disabled || loading;
  const palette = buttonPalette[variant];

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
        { backgroundColor: palette.bg, borderColor: palette.border },
        pressed && !isDisabled && styles.buttonPressed,
        isDisabled && styles.buttonDisabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={palette.fg} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={18} color={palette.fg} /> : null}
          <Text style={[styles.buttonLabel, { color: palette.fg }]}>{label}</Text>
        </>
      )}
    </Pressable>
  );
}

const buttonPalette: Record<ButtonVariant, { bg: string; fg: string; border: string }> = {
  primary: { bg: colors.accent, fg: "#0d0d0d", border: colors.accent },
  secondary: { bg: colors.card, fg: colors.text, border: colors.border },
  ghost: { bg: "transparent", fg: colors.text, border: colors.border },
  danger: { bg: "transparent", fg: colors.danger, border: colors.danger },
};

// ---------------------------------------------------------------------------
// Screen states
// ---------------------------------------------------------------------------

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <View style={styles.centered} accessibilityRole="progressbar">
      <ActivityIndicator color={colors.accent} size="large" />
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
  return (
    <View style={styles.centered}>
      <Ionicons
        name={icon}
        size={44}
        color={tone === "error" ? colors.danger : colors.muted}
      />
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

export function Divider() {
  return <View style={styles.divider} />;
}

const styles = StyleSheet.create({
  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    minHeight: 52, // Apple's 44pt minimum touch target, with room to breathe.
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    borderWidth: 1,
  },
  buttonPressed: { opacity: 0.8 },
  buttonDisabled: { opacity: 0.45 },
  buttonLabel: { ...typography.label, fontSize: 15 },

  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.xl,
    gap: spacing.sm,
  },
  stateTitle: { ...typography.heading, color: colors.text, marginTop: spacing.sm },
  stateSubtitle: {
    ...typography.body,
    color: colors.muted,
    textAlign: "center",
    maxWidth: 280,
  },
  stateAction: { marginTop: spacing.md, minWidth: 200 },

  header: { paddingHorizontal: spacing.md, paddingTop: spacing.sm, paddingBottom: spacing.md },
  headerTitle: { ...typography.display, color: colors.text },
  headerSubtitle: { ...typography.body, color: colors.muted, marginTop: spacing.xs },

  divider: { height: 1, backgroundColor: colors.border, marginVertical: spacing.md },
});
