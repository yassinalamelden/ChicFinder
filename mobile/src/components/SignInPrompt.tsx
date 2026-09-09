/**
 * Shown wherever a guest hits something that needs an account.
 *
 * Browsing and searching are open; only the things tied to a person (a
 * wishlist, an account) ask for sign-in, and they ask at the moment the user
 * reaches for them rather than at the front door.
 */

import React from "react";
import { View } from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

import { Button, MessageState } from "./ui";
import { spacing } from "../theme";

interface SignInPromptProps {
  title: string;
  subtitle: string;
  icon?: keyof typeof Ionicons.glyphMap;
  /** Label for the primary action. */
  cta?: string;
}

export function SignInPrompt({
  title,
  subtitle,
  icon = "person-circle-outline",
  cta = "Sign in",
}: SignInPromptProps) {
  const router = useRouter();

  return (
    <MessageState
      icon={icon}
      title={title}
      subtitle={subtitle}
      action={
        <View style={{ gap: spacing.sm + 2, width: "100%" }}>
          <Button
            label={cta}
            variant="accent"
            arrow
            onPress={() => router.push("/(auth)/welcome")}
          />
        </View>
      }
    />
  );
}
