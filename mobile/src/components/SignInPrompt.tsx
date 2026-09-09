/**
 * Shown wherever a guest hits something that needs an account.
 *
 * Browsing and searching are open; only the things tied to a person (a
 * wishlist, an account) ask for sign-in, and they ask at the moment the user
 * reaches for them rather than at the front door.
 */

import React from "react";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

import { Button, MessageState } from "./ui";

interface SignInPromptProps {
  title: string;
  subtitle: string;
  icon?: keyof typeof Ionicons.glyphMap;
  /** Label for the primary action. */
  cta?: string;
  /** Passed straight through to MessageState. */
  align?: "center" | "top";
}

export function SignInPrompt({
  title,
  subtitle,
  icon = "person-circle-outline",
  cta = "Sign in",
  align = "center",
}: SignInPromptProps) {
  const router = useRouter();

  return (
    <MessageState
      icon={icon}
      title={title}
      subtitle={subtitle}
      align={align}
      action={
        <Button
          label={cta}
          variant="accent"
          arrow
          onPress={() => router.push("/(auth)/welcome")}
        />
      }
    />
  );
}
