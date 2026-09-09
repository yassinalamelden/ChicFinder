/**
 * Authentication state and sign-in methods.
 *
 * Three ways in:
 *   - Sign in with Apple (required by App Store Guideline 4.8 whenever an app
 *     offers another social login, which this one does)
 *   - Google
 *   - Email and password
 *
 * Apple sign-in only returns the user's name on the very first authorisation,
 * so it is written to the Firebase profile immediately. Asking Apple again
 * later returns nothing, and there is no way to recover it.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Platform } from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";
import * as Crypto from "expo-crypto";
import * as Google from "expo-auth-session/providers/google";
import * as WebBrowser from "expo-web-browser";
import {
  GoogleAuthProvider,
  OAuthProvider,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithCredential,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  updateProfile,
  type User,
} from "firebase/auth";

import { auth, isFirebaseConfigured, requireAuth } from "../lib/firebase";

WebBrowser.maybeCompleteAuthSession();

export class AuthError extends Error {}

interface AuthContextValue {
  user: User | null;
  initialising: boolean;
  isAppleAvailable: boolean;
  isGoogleReady: boolean;
  signInWithApple: () => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  registerWithEmail: (email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Turns Firebase's error codes into something worth showing a person. */
function humanise(err: unknown): string {
  const code = (err as { code?: string })?.code ?? "";
  switch (code) {
    case "auth/invalid-email":
      return "That email address does not look right.";
    case "auth/invalid-credential":
    case "auth/wrong-password":
    case "auth/user-not-found":
      return "Email or password is incorrect.";
    case "auth/email-already-in-use":
      return "An account already exists with that email. Try signing in.";
    case "auth/weak-password":
      return "Pick a password with at least 6 characters.";
    case "auth/too-many-requests":
      return "Too many attempts. Please wait a minute and try again.";
    case "auth/network-request-failed":
      return "Network problem. Check your connection and try again.";
    default:
      return (err as Error)?.message ?? "Sign-in failed. Please try again.";
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initialising, setInitialising] = useState(true);
  const [isAppleAvailable, setAppleAvailable] = useState(false);

  // Google sign-in via the system browser. The client IDs are public.
  const [googleRequest, googleResponse, promptGoogle] = Google.useIdTokenAuthRequest({
    iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
    androidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
    webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
  });

  useEffect(() => {
    if (!isFirebaseConfigured) {
      setInitialising(false);
      return;
    }
    return onAuthStateChanged(requireAuth(), (next) => {
      setUser(next);
      setInitialising(false);
    });
  }, []);

  useEffect(() => {
    if (Platform.OS !== "ios") return;
    AppleAuthentication.isAvailableAsync().then(setAppleAvailable).catch(() => {});
  }, []);

  // Exchange Google's id token for a Firebase session once the browser returns.
  useEffect(() => {
    if (googleResponse?.type !== "success") return;
    const idToken = googleResponse.params?.id_token;
    if (!idToken) return;
    signInWithCredential(requireAuth(), GoogleAuthProvider.credential(idToken)).catch((err) => {
      console.warn("Google sign-in failed", err);
    });
  }, [googleResponse]);

  const signInWithApple = useCallback(async () => {
    try {
      // A nonce binds Apple's response to this request. Apple hashes what we
      // send, so Firebase gets the raw value and Apple gets the SHA-256 of it.
      const rawNonce = Crypto.randomUUID();
      const hashedNonce = await Crypto.digestStringAsync(
        Crypto.CryptoDigestAlgorithm.SHA256,
        rawNonce
      );

      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
        nonce: hashedNonce,
      });

      if (!credential.identityToken) {
        throw new AuthError("Apple did not return a sign-in token. Please try again.");
      }

      const provider = new OAuthProvider("apple.com");
      const result = await signInWithCredential(
        requireAuth(),
        provider.credential({
          idToken: credential.identityToken,
          rawNonce,
        })
      );

      // Apple hands over the name exactly once, on first authorisation.
      const given = credential.fullName?.givenName;
      const family = credential.fullName?.familyName;
      if ((given || family) && !result.user.displayName) {
        await updateProfile(result.user, {
          displayName: [given, family].filter(Boolean).join(" "),
        });
      }
    } catch (err) {
      // The user backing out of the Apple sheet is not an error worth surfacing.
      if ((err as { code?: string }).code === "ERR_REQUEST_CANCELED") return;
      throw new AuthError(humanise(err));
    }
  }, []);

  const signInWithGoogle = useCallback(async () => {
    if (!googleRequest) {
      throw new AuthError("Google sign-in is not configured yet.");
    }
    const result = await promptGoogle();
    if (result.type === "error") {
      throw new AuthError("Google sign-in failed. Please try again.");
    }
  }, [googleRequest, promptGoogle]);

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    try {
      await signInWithEmailAndPassword(requireAuth(), email.trim(), password);
    } catch (err) {
      throw new AuthError(humanise(err));
    }
  }, []);

  const registerWithEmail = useCallback(async (email: string, password: string) => {
    try {
      await createUserWithEmailAndPassword(requireAuth(), email.trim(), password);
    } catch (err) {
      throw new AuthError(humanise(err));
    }
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    try {
      await sendPasswordResetEmail(requireAuth(), email.trim());
    } catch (err) {
      throw new AuthError(humanise(err));
    }
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(requireAuth());
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      initialising,
      isAppleAvailable,
      isGoogleReady: Boolean(googleRequest),
      signInWithApple,
      signInWithGoogle,
      signInWithEmail,
      registerWithEmail,
      resetPassword,
      signOut,
    }),
    [
      user,
      initialising,
      isAppleAvailable,
      googleRequest,
      signInWithApple,
      signInWithGoogle,
      signInWithEmail,
      registerWithEmail,
      resetPassword,
      signOut,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside an AuthProvider.");
  return ctx;
}
