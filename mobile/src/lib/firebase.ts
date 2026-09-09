/**
 * Firebase initialisation for React Native.
 *
 * Two things differ from the web setup:
 *
 *  1. Auth has to be created with initializeAuth + getReactNativePersistence.
 *     The default getAuth() keeps the session in memory only, so the user would
 *     be signed out every cold start.
 *  2. Config comes from EXPO_PUBLIC_* env vars, which Expo inlines at build
 *     time. These are public client identifiers, not secrets, exactly as on the
 *     web. Real access control lives in Firebase security rules and in the
 *     backend's token verification.
 */

import { initializeApp, getApps, getApp, type FirebaseOptions } from "firebase/app";
import {
  initializeAuth,
  getAuth,
  // @ts-expect-error: not in firebase's public types, but is the documented RN export
  getReactNativePersistence,
  type Auth,
} from "firebase/auth";
import AsyncStorage from "@react-native-async-storage/async-storage";

const firebaseConfig: FirebaseOptions = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID,
};

export const isFirebaseConfigured = Boolean(
  firebaseConfig.apiKey && firebaseConfig.projectId && firebaseConfig.appId
);

const app = getApps().length ? getApp() : initializeApp(firebaseConfig);

function createAuth(): Auth {
  try {
    return initializeAuth(app, {
      persistence: getReactNativePersistence(AsyncStorage),
    });
  } catch {
    // initializeAuth throws if it already ran, which happens on Fast Refresh.
    return getAuth(app);
  }
}

export const auth = createAuth();
export { app };
