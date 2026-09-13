import type { ExpoConfig, ConfigContext } from "expo/config";

/**
 * Expo config for the ChicFinder iOS/Android app.
 *
 * Secrets are read from the environment (EAS build secrets in CI, a local .env
 * for development) rather than committed, so this file is safe in the repo.
 * See mobile/.env.example for the full list.
 */

const BUNDLE_ID = "app.chicfinder.mobile";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * The hostname of the API, but only when it is served over plain HTTP.
 *
 * iOS App Transport Security refuses cleartext connections, so a build pointed
 * at `http://…` cannot reach its own backend without an explicit exception.
 * The ChicFinder API currently runs on an ALB with no TLS listener, because a
 * certificate needs a domain nobody has registered yet.
 *
 * Deriving the exception from the URL rather than hardcoding it means the
 * exception disappears by itself the moment the API moves to https, instead of
 * lingering in the Info.plist until someone remembers to delete it. That
 * matters: Apple reviews ATS exceptions and rejects ones without justification,
 * so shipping a build that still carries this is a submission risk.
 */
function cleartextHost(url: string): string | null {
  if (!url.startsWith("http://")) return null;
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

const INSECURE_HOST = cleartextHost(API_URL);

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "ChicFinder",
  slug: "chicfinder",
  scheme: "chicfinder",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "automatic",
  backgroundColor: "#edeae2",
  primaryColor: "#e9a03c",
  assetBundlePatterns: ["**/*"],

  // The splash screen is configured through the expo-splash-screen plugin below;
  // the top-level `splash` key was removed in SDK 54.

  ios: {
    bundleIdentifier: BUNDLE_ID,
    supportsTablet: false,
    // Apple requires an export-compliance answer on every build. The app uses
    // only standard HTTPS, which is exempt, so declaring it here stops App Store
    // Connect asking on each upload.
    config: { usesNonExemptEncryption: false },
    infoPlist: {
      // Permission strings are shown verbatim in the iOS prompt. Apple rejects
      // vague ones, so each says what the app does with the data.
      NSCameraUsageDescription:
        "ChicFinder uses your camera so you can photograph an outfit and find similar items from Egyptian brands.",
      NSPhotoLibraryUsageDescription:
        "ChicFinder needs access to your photos so you can choose an outfit picture to search with.",

      // TEMPORARY, and scoped to exactly one host. Remove by giving the API a
      // domain and an HTTPS listener, at which point this block stops being
      // generated on its own. Never widen this to NSAllowsArbitraryLoads.
      ...(INSECURE_HOST
        ? {
            NSAppTransportSecurity: {
              NSExceptionDomains: {
                [INSECURE_HOST]: {
                  NSExceptionAllowsInsecureHTTPLoads: true,
                  NSIncludesSubdomains: false,
                },
              },
            },
          }
        : {}),
    },
    // Sign in with Apple. Required by Guideline 4.8 because the app also offers
    // Google sign-in.
    usesAppleSignIn: true,
  },

  android: {
    package: BUNDLE_ID,
    adaptiveIcon: {
      foregroundImage: "./assets/android-icon-foreground.png",
      backgroundColor: "#0e0f0b",
    },
    permissions: ["android.permission.CAMERA"],
  },

  web: {
    bundler: "metro",
    output: "static",
    favicon: "./assets/favicon.png",
  },

  plugins: [
    "expo-router",
    "expo-apple-authentication",
    "expo-secure-store",
    [
      "expo-image-picker",
      {
        photosPermission:
          "ChicFinder needs access to your photos so you can choose an outfit picture to search with.",
        cameraPermission:
          "ChicFinder uses your camera so you can photograph an outfit and find similar items from Egyptian brands.",
      },
    ],
    [
      "expo-splash-screen",
      {
        image: "./assets/splash-icon.png",
        resizeMode: "contain",
        backgroundColor: "#edeae2",
        // The app follows the phone's appearance, so the launch screen has to
        // as well. Without this, a dark-mode launch shows an ink mark on bone
        // and then snaps to a near-black first screen.
        dark: {
          image: "./assets/splash-icon-dark.png",
          resizeMode: "contain",
          backgroundColor: "#14150f",
        },
      },
    ],
  ],

  experiments: {
    typedRoutes: true,
  },

  extra: {
    apiUrl: API_URL,
    privacyPolicyUrl:
      process.env.EXPO_PUBLIC_PRIVACY_POLICY_URL ??
      "https://chicfinder.app/privacy",
    supportEmail: process.env.EXPO_PUBLIC_SUPPORT_EMAIL ?? "support@chicfinder.app",
    eas: {
      // Filled in by `eas init`. Leave as-is until the project is created.
      projectId: process.env.EAS_PROJECT_ID ?? undefined,
    },
  },
});
