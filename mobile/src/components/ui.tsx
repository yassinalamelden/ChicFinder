/**
 * Shared building blocks: buttons, screen chrome, empty and error states.
 *
 * Everything reads its colours through `useThemedStyles`, so light and dark are
 * the same component with a different palette rather than two code paths.
 */

import React, { type ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  Text,
  View,
  StyleSheet,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import {
  elevation,
  radius,
  spacing,
  typography,
  useTheme,
  useThemedStyles,
  type Palette,
} from "../theme";

// ---------------------------------------------------------------------------
// Button
// ---------------------------------------------------------------------------

type ButtonVariant = "primary" | "accent" | "secondary" | "danger";

interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  icon?: keyof typeof Ionicons.glyphMap;
  /** Adds the circular arrow badge. Forward-moving actions only. */
  arrow?: boolean;
  loading?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  hint?: string;
}

function palette(c: Palette, variant: ButtonVariant) {
  switch (variant) {
    case "primary":
      return { bg: c.contrast, fg: c.onContrast, border: c.contrast, badge: "rgba(127,127,127,0.22)" };
    case "accent":
      return { bg: c.accent, fg: c.onAccent, border: c.accent, badge: "rgba(30,35,0,0.14)" };
    case "secondary":
      return { bg: "transparent", fg: c.text, border: c.border, badge: "rgba(127,127,127,0.14)" };
    case "danger":
      return { bg: "transparent", fg: c.danger, border: c.danger, badge: c.dangerSoft };
  }
}

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
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const tone = palette(colors, variant);
  const isDisabled = disabled || loading;

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
        // A small scale on press is the cheapest thing that makes a control
        // feel native rather than like a web button.
        pressed && !isDisabled && styles.buttonPressed,
        isDisabled && styles.buttonDisabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={tone.fg} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={19} color={tone.fg} /> : null}
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
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
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
  const colors = useTheme();
  const styles = useThemedStyles(makeStyles);
  const isError = tone === "error";
  return (
    <View style={styles.centered}>
      <View style={[styles.stateRing, isError && { backgroundColor: colors.dangerSoft }]}>
        <Ionicons name={icon} size={32} color={isError ? colors.danger : colors.accent} />
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
  const styles = useThemedStyles(makeStyles);
  return (
    <View style={styles.header}>
      <Text style={styles.headerTitle} accessibilityRole="header">
        {title}
      </Text>
      {subtitle ? <Text style={styles.headerSubtitle}>{subtitle}</Text> : null}
    </View>
  );
}

export function Label({ children }: { children: ReactNode }) {
  const styles = useThemedStyles(makeStyles);
  return <Text style={styles.label}>{children}</Text>;
}

/** Card surface with the app's standard elevation. */
export function Card({
  children,
  style,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const styles = useThemedStyles(makeStyles);
  return <View style={[styles.card, style]}>{children}</View>;
}

const makeStyles = (c: Palette) => ({
  button: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    gap: spacing.sm + 2,
    minHeight: 56,
    paddingHorizontal: spacing.lg + 4,
    borderRadius: radius.pill,
    borderWidth: 1,
  },
  buttonWithArrow: { paddingRight: spacing.sm },
  buttonPressed: { opacity: 0.85, transform: [{ scale: 0.985 }] },
  buttonDisabled: { opacity: 0.4 },
  buttonLabel: typography.button,
  arrowBadge: {
    width: 32,
    height: 32,
    borderRadius: radius.pill,
    alignItems: "center" as const,
    justifyContent: "center" as const,
  },

  centered: {
    flex: 1,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    padding: spacing.xl,
    gap: spacing.sm,
  },
  stateRing: {
    width: 76,
    height: 76,
    borderRadius: radius.pill,
    backgroundColor: c.accentSoft,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    marginBottom: spacing.xs,
  },
  stateTitle: { ...typography.title, color: c.text, textAlign: "center" as const },
  stateSubtitle: {
    ...typography.body,
    color: c.muted,
    textAlign: "center" as const,
    maxWidth: 270,
  },
  stateAction: { marginTop: spacing.md, minWidth: 210 },

  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xs,
    paddingBottom: spacing.lg,
  },
  headerTitle: { ...typography.display, color: c.text },
  headerSubtitle: { ...typography.body, color: c.muted, marginTop: spacing.xs },

  label: { ...typography.label, color: c.faint },

  card: {
    backgroundColor: c.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: c.border,
    ...elevation(c, 1),
  },
});
