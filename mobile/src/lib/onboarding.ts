/**
 * Whether the first-launch walkthrough has been seen.
 *
 * Deliberately device-local rather than tied to the account: the walkthrough
 * explains how the app works, and a guest is exactly who needs it. Waiting for
 * a sign-in to find out would defeat the point.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "chicfinder.onboarded";

/**
 * `null` means "not known yet". The caller must not decide anything on a
 * pending read, or a cold start flashes the walkthrough at someone who has
 * already dismissed it.
 */
export async function hasOnboarded(): Promise<boolean> {
  try {
    return (await AsyncStorage.getItem(KEY)) === "1";
  } catch {
    // Unreadable storage should not trap the user in a loop of walkthroughs.
    return true;
  }
}

export async function markOnboarded(): Promise<void> {
  try {
    await AsyncStorage.setItem(KEY, "1");
  } catch {
    /* ignore: worst case they see it once more */
  }
}

/** Only used by a debug path; kept so the flag is not write-only. */
export async function resetOnboarding(): Promise<void> {
  try {
    await AsyncStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
