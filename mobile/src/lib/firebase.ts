/**
 * Firebase initialisation for React Native.
 *
 * Two things differ from the web setup:
 *
 *  1. Auth is created with initializeAuth + getReactNativePersistence. The
 *     default getAuth() keeps the session in memory only, so the user would be
 *     signed out on every cold start. getReactNativePersistence only exists in
 *     Firebase's "react-native" export condition, which is why
 *     metro.config.js must leave package exports enabled.
 *  2. Config comes from EXPO_PUBLIC_* env vars, which Expo inlines at build
 *     time. These are public client identifiers, not secrets, exactly as on the
 *     web. Real access control lives in Firebase security rules and in the
 *     backend's token verification.
 *
 * When the config is absent or incomplete, this module does NOT initialise
 * Firebase and exports `auth` as null. Initialising with a blank key throws
 * during module evaluation, which cascades into every screen that imports this
 * file failing to load, and the app dies with a stack of unrelated
 * "missing default export" errors. Failing softly here keeps the app bootable
 * and lets the UI say what is actually wrong.
 */

import { initializeApp, getApps, getApp, type FirebaseApp, type FirebaseOptions } from "firebase/app";
import {
  initializeAuth,
  getAuth,
  type Auth,
  type Persistence,
} from "firebase/auth";
import * as firebaseAuth from "firebase/auth";
import AsyncStorage from "@react-native-async-storage/async-storage";

/**
 * getReactNativePersistence is real at runtime but absent from the published
 * types: Firebase's "types" field points at the web build's declarations while
 * the "react-native" export condition serves the RN build. So it is read off
 * the namespace with a narrow cast, and its absence is treated as fatal.
 *
 * The absence check is the important part. Previously this was a blanket
 * @ts-expect-error and the value was silently undefined whenever Metro resolved
 * the web build, which turned a resolver misconfiguration into a bogus
 * auth/invalid-api-key error several layers away.
 */
const getReactNativePersistence = (
  firebaseAuth as unknown as {
    getReactNativePersistence?: (storage: unknown) => Persistence;
  }
).getReactNativePersistence;

const firebaseConfig: FirebaseOptions = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID,
};

/** A placeholder copied from .env.example is not a real value. */
function looksReal(value: string | undefined): boolean {
  if (!value) return false;
  const v = value.trim();
  if (!v) return false;
  return !/^(your_|xxx|changeme|placeholder|<)/i.test(v);
}

export const isFirebaseConfigured =
  looksReal(firebaseConfig.apiKey) &&
  looksReal(firebaseConfig.projectId) &&
  looksReal(firebaseConfig.appId);

/** Names the missing pieces, so the UI can tell the user what to fill in. */
export const missingFirebaseKeys: string[] = [
  ["EXPO_PUBLIC_FIREBASE_API_KEY", firebaseConfig.apiKey],
  ["EXPO_PUBLIC_FIREBASE_PROJECT_ID", firebaseConfig.projectId],
  ["EXPO_PUBLIC_FIREBASE_APP_ID", firebaseConfig.appId],
]
  .filter(([, value]) => !looksReal(value as string | undefined))
  .map(([name]) => name as string);

function createAuth(instance: FirebaseApp): Auth {
  if (typeof getReactNativePersistence !== "function") {
    throw new Error(
      "firebase/auth resolved to its web build, so React Native persistence is " +
        "unavailable. Check that metro.config.js has not disabled package exports " +
        "(config.resolver.unstable_enablePackageExports must stay enabled)."
    );
  }
  try {
    return initializeAuth(instance, {
      persistence: getReactNativePersistence(AsyncStorage),
    });
  } catch (err) {
    // Fast Refresh re-runs this module, and initializeAuth refuses to run twice.
    // Anything else is a real fault and must not be swallowed: silently falling
    // back to getAuth() is what turned a missing-persistence bug into a
    // misleading auth/invalid-api-key error.
    if ((err as { code?: string })?.code === "auth/already-initialized") {
      return getAuth(instance);
    }
    throw err;
  }
}

let appInstance: FirebaseApp | null = null;
let authInstance: Auth | null = null;

if (isFirebaseConfigured) {
  appInstance = getApps().length ? getApp() : initializeApp(firebaseConfig);
  authInstance = createAuth(appInstance);
} else {
  console.warn(
    `[ChicFinder] Firebase is not configured. Missing: ${missingFirebaseKeys.join(
      ", "
    )}. Sign-in is disabled until mobile/.env has real values from the Firebase console.`
  );
}

export const app = appInstance;
export const auth = authInstance;

/** Use inside handlers. Throws a message worth showing rather than a crash. */
export function requireAuth(): Auth {
  if (!authInstance) {
    throw new Error(
      "Sign-in is unavailable because Firebase is not configured on this build."
    );
  }
  return authInstance;
}
